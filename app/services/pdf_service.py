"""PDF generation service for invoices using WeasyPrint."""
import os
from datetime import datetime
from flask import render_template
from app import db
from app.models import Faktura


def get_template(faktura):
    """
    Get the appropriate PDF template based on invoice language.

    Args:
        faktura: Faktura model instance

    Returns:
        str: Template path ('pdf/faktura_sr.html' or 'pdf/faktura_en.html')
    """
    if faktura.jezik == 'en':
        return 'pdf/faktura_en.html'
    return 'pdf/faktura_sr.html'


def render_pdf_template(faktura, template_name):
    """
    Render Jinja2 template with faktura context.

    Args:
        faktura: Faktura model instance
        template_name: Template file path

    Returns:
        str: Rendered HTML string (UTF-8 encoded)
    """
    from flask import current_app

    # Get absolute font paths for template
    fonts_dir = os.path.join(current_app.root_path, 'static', 'fonts')
    font_normal = os.path.join(fonts_dir, 'DejaVuSansCondensed.ttf')
    font_bold = os.path.join(fonts_dir, 'DejaVuSansCondensed-Bold.ttf')

    # Prepare context for template rendering (no Flask request context needed)
    context = {
        'faktura': faktura,
        'firma': faktura.firma,
        'komitent': faktura.komitent,
        'stavke': faktura.stavke,
        'today': datetime.now(),
        # Add font paths to context for @font-face
        'font_normal_path': font_normal.replace('\\', '/'),
        'font_bold_path': font_bold.replace('\\', '/')
    }

    # Load template directly from Jinja2 environment (bypasses Flask context processors)
    template_path = current_app.jinja_env.get_or_select_template(template_name)

    # Render template with explicit context only (no current_user, no session, etc.)
    html_content = template_path.render(**context)

    # Ensure HTML is properly encoded as UTF-8 string
    if isinstance(html_content, bytes):
        html_content = html_content.decode('utf-8')

    return html_content


def ensure_storage_folder(firma_id, godina, mesec):
    """
    Create storage folder structure if it doesn't exist.

    Args:
        firma_id: PausalnFirma ID
        godina: Year (e.g., 2025)
        mesec: Month (e.g., 1, 2, ..., 12)

    Returns:
        str: Path to storage folder
    """
    folder_path = os.path.join('storage', 'fakture', str(firma_id), str(godina), f'{mesec:02d}')
    os.makedirs(folder_path, exist_ok=True)
    return folder_path


def generate_pdf(faktura):
    """
    Generate PDF from faktura using WeasyPrint (with xhtml2pdf fallback for Windows).

    Args:
        faktura: Faktura model instance

    Returns:
        bytes: PDF content as bytes

    Raises:
        ValueError: If PDF generation fails
    """
    # Get appropriate template
    template_name = get_template(faktura)

    # Render HTML template
    html_string = render_pdf_template(faktura, template_name)

    # Try WeasyPrint first (works on Linux production)
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_string).write_pdf()
        return pdf_bytes

    except (ImportError, OSError) as weasy_error:
        # WeasyPrint not available (Windows/GTK issue) - fallback to xhtml2pdf
        try:
            from xhtml2pdf import pisa
            from io import BytesIO
            from flask import current_app
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.fonts import addMapping

            # Get font directory
            fonts_dir = os.path.join(current_app.root_path, 'static', 'fonts')

            # Font paths
            font_normal = os.path.join(fonts_dir, 'DejaVuSansCondensed.ttf')
            font_bold = os.path.join(fonts_dir, 'DejaVuSansCondensed-Bold.ttf')

            # Register fonts with reportlab
            try:
                pdfmetrics.registerFont(TTFont('DejaVuSans', font_normal))
                pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', font_bold))

                # Register font family mapping
                addMapping('DejaVuSans', 0, 0, 'DejaVuSans')          # normal
                addMapping('DejaVuSans', 1, 0, 'DejaVuSans-Bold')     # bold
                addMapping('DejaVuSans', 0, 1, 'DejaVuSans')          # italic (use normal)
                addMapping('DejaVuSans', 1, 1, 'DejaVuSans-Bold')     # bold+italic (use bold)
            except Exception as e:
                current_app.logger.warning(f"Font registration warning: {e}")

            # Link callback to handle font loading
            def link_callback(uri, rel):
                """
                Handle file loading for xhtml2pdf (fonts, images, etc.).

                This callback resolves relative URIs to absolute file paths.
                """
                current_app.logger.debug(f"link_callback called: uri={uri}, rel={rel}")

                # Remove file:// protocol if present
                if uri.startswith('file://'):
                    uri = uri[7:]

                # Handle relative font paths (from @font-face declarations)
                if uri.endswith('.ttf'):
                    # Try direct filename in fonts directory
                    font_path = os.path.join(fonts_dir, os.path.basename(uri))
                    current_app.logger.debug(f"Checking font path: {font_path}, exists={os.path.exists(font_path)}")
                    if os.path.exists(font_path):
                        current_app.logger.info(f"Font found: {font_path}")
                        return font_path

                # Handle app/static/fonts paths (if specified with full path)
                if uri.startswith('app/static/fonts/'):
                    font_filename = uri.replace('app/static/fonts/', '')
                    font_path = os.path.join(fonts_dir, font_filename)
                    if os.path.exists(font_path):
                        return font_path

                # Return as-is if not found
                current_app.logger.warning(f"Font NOT found for URI: {uri}")
                return uri

            # Create PDF with UTF-8 encoding and font callback
            pdf_buffer = BytesIO()

            # Ensure HTML string is bytes with UTF-8 encoding
            if isinstance(html_string, str):
                html_bytes = html_string.encode('utf-8')
            else:
                html_bytes = html_string

            pisa_status = pisa.CreatePDF(
                html_bytes,
                dest=pdf_buffer,
                encoding='utf-8',
                link_callback=link_callback
            )

            if pisa_status.err:
                raise ValueError("xhtml2pdf generation failed with errors")

            pdf_bytes = pdf_buffer.getvalue()
            pdf_buffer.close()

            return pdf_bytes

        except Exception as xhtml_error:
            raise ValueError(f"PDF generation failed - WeasyPrint: {weasy_error}, xhtml2pdf: {xhtml_error}")


def save_pdf(pdf_bytes, faktura):
    """
    Save PDF to disk and update faktura model.

    Args:
        pdf_bytes: PDF content as bytes
        faktura: Faktura model instance

    Returns:
        str: Path to saved PDF file
    """
    # Extract date components from faktura
    godina = faktura.datum_prometa.year
    mesec = faktura.datum_prometa.month

    # Ensure folder structure exists
    folder_path = ensure_storage_folder(faktura.firma_id, godina, mesec)

    # Sanitize broj_fakture for filename (replace / with -)
    safe_filename = faktura.broj_fakture.replace('/', '-')
    filename = f'{safe_filename}.pdf'

    # Full file path
    file_path = os.path.join(folder_path, filename)

    # Write PDF to disk
    with open(file_path, 'wb') as f:
        f.write(pdf_bytes)

    # Update faktura model with PDF path
    faktura.pdf_url = file_path
    faktura.status_pdf = 'generated'
    db.session.commit()

    return file_path
