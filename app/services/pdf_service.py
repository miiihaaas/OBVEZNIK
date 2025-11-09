"""PDF generation service for invoices using WeasyPrint."""
import os
from datetime import datetime
from flask import render_template
from app import db
from app.models import Faktura


def get_template(faktura):
    """
    Get the appropriate PDF template based on invoice type and language.

    Args:
        faktura: Faktura model instance

    Returns:
        str: Template path (e.g., 'pdf/profaktura_sr.html', 'pdf/faktura_en.html', 'pdf/avansna_sr.html')

    Business Rules:
        - Profakture use separate templates with PROFAKTURA/PROFORMA INVOICE watermark (Story 4.1)
        - Avansne fakture use separate templates with AVANSNA FAKTURA/ADVANCE INVOICE watermark (Story 4.3)
        - Standardne fakture use standard templates
        - Serbian invoices use '_sr.html' templates
        - Foreign currency invoices use '_en.html' templates (jezik='en')
    """
    if faktura.tip_fakture == 'profaktura':
        # Profaktura templates with watermark
        if faktura.jezik == 'en':
            return 'pdf/profaktura_en.html'
        return 'pdf/profaktura_sr.html'
    elif faktura.tip_fakture == 'avansna':
        # Avansna faktura templates with watermark (Story 4.3)
        if faktura.jezik == 'en':
            return 'pdf/avansna_en.html'
        return 'pdf/avansna_sr.html'
    else:
        # Standardna faktura templates
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
        from flask import current_app

        # WeasyPrint requires @font-face for custom fonts
        # Inject @font-face CSS before <style> tag
        fonts_dir = os.path.join(current_app.root_path, 'static', 'fonts')
        font_normal = os.path.join(fonts_dir, 'DejaVuSansCondensed.ttf')
        font_bold = os.path.join(fonts_dir, 'DejaVuSansCondensed-Bold.ttf')

        font_face_css = f"""
        @font-face {{
            font-family: 'DejaVuSans';
            src: url('file://{font_normal.replace(os.sep, '/')}');
            font-weight: normal;
            font-style: normal;
        }}
        @font-face {{
            font-family: 'DejaVuSans';
            src: url('file://{font_bold.replace(os.sep, '/')}');
            font-weight: bold;
            font-style: normal;
        }}
        """

        # Inject font-face CSS after <style> tag
        html_with_fonts = html_string.replace('<style>', f'<style>\n{font_face_css}')

        pdf_bytes = HTML(string=html_with_fonts).write_pdf()
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

                xhtml2pdf has a known bug with @font-face embedding. Instead of using
                @font-face, we rely on reportlab font registration (lines 128-135 above).
                Returning None tells xhtml2pdf to skip @font-face and use registered fonts.
                """
                current_app.logger.debug(f"link_callback called: uri={uri}, rel={rel}")

                # For font files: ignore @font-face and use reportlab-registered fonts
                if uri.endswith('.ttf') or uri.endswith('.otf'):
                    current_app.logger.info(f"Ignoring @font-face for {uri}, using reportlab fonts")
                    return None

                # Handle /static/ URLs by converting to absolute file paths
                if uri.startswith('/static/'):
                    static_path = os.path.join(current_app.root_path, 'static', uri[8:])  # Remove '/static/' prefix
                    current_app.logger.debug(f"Resolved /static/ URI to: {static_path}")
                    return static_path

                # Handle other resources (images, CSS, etc.) if needed in future
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


def generate_kpo_pdf(kpo_entries, firma, filters, total_promet):
    """
    Generate PDF for KPO knjiga (Knjiga Prometa Obveznika).

    Args:
        kpo_entries: List of KPOEntry objects
        firma: PausalnFirma object (can be None for admin god mode)
        filters: Dict with applied filters (for display in PDF header)
        total_promet: Decimal - Total promet sum

    Returns:
        bytes: PDF file content

    Compliance:
        NFR16 - Pravilnik o vođenju poslovnih knjiga
        A4 Landscape format for wide tables
    """
    import logging

    logger = logging.getLogger(__name__)

    # Render HTML template
    html_content = render_template(
        'pdf/kpo_knjiga.html',
        kpo_entries=kpo_entries,
        firma=firma,
        filters=filters,
        total_promet=total_promet,
        generated_at=datetime.now()
    )

    # Try WeasyPrint first (works on Linux production)
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration

        # WeasyPrint configuration
        font_config = FontConfiguration()

        # Custom CSS for A4 landscape
        landscape_css = CSS(string='''
            @page {
                size: A4 landscape;
                margin: 1.5cm 1cm;
            }
            body {
                font-family: 'DejaVu Sans', Arial, sans-serif;
                font-size: 9pt;
            }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                padding: 4px 6px;
                border: 1px solid #ccc;
            }
            th {
                background-color: #f0f0f0;
                font-weight: bold;
            }
            .text-right {
                text-align: right;
            }
            .text-center {
                text-align: center;
            }
        ''', font_config=font_config)

        # Generate PDF with WeasyPrint
        pdf_bytes = HTML(string=html_content).write_pdf(
            stylesheets=[landscape_css],
            font_config=font_config
        )

        logger.info(f"KPO PDF generated successfully with WeasyPrint: {len(kpo_entries)} entries, firma={firma.naziv if firma else 'All'}")

        return pdf_bytes

    except (ImportError, OSError) as weasy_error:
        # WeasyPrint not available (Windows/GTK issue) - fallback to xhtml2pdf
        logger.warning(f"WeasyPrint failed ({weasy_error}), falling back to xhtml2pdf")

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
                logger.warning(f"Font registration warning: {e}")

            # Link callback to handle font loading
            def link_callback(uri, rel):
                """Handle file loading for xhtml2pdf (fonts, images, etc.)."""
                logger.debug(f"link_callback called: uri={uri}, rel={rel}")

                # For font files: ignore @font-face and use reportlab-registered fonts
                if uri.endswith('.ttf') or uri.endswith('.otf'):
                    logger.info(f"Ignoring @font-face for {uri}, using reportlab fonts")
                    return None

                # Handle /static/ URLs by converting to absolute file paths
                if uri.startswith('/static/'):
                    static_path = os.path.join(current_app.root_path, 'static', uri[8:])
                    logger.debug(f"Resolved /static/ URI to: {static_path}")
                    return static_path

                return uri

            # Clean HTML for xhtml2pdf compatibility (remove @bottom-center and other margin box rules)
            import re

            # Remove @bottom-center, @top-center, etc. (not supported by xhtml2pdf)
            html_cleaned = re.sub(r'@(bottom|top|left|right)-(left|center|right)\s*\{[^}]*\}', '', html_content, flags=re.DOTALL)

            # Simplify @page rule - remove nested rules
            html_cleaned = re.sub(r'@page\s*\{[^}]*(@[^}]*\}[^}]*)*\}', '@page { size: A4 landscape; margin: 1.5cm 1cm; }', html_cleaned, flags=re.DOTALL)

            logger.debug("HTML cleaned for xhtml2pdf compatibility")

            # Create PDF with UTF-8 encoding and font callback
            pdf_buffer = BytesIO()

            # Ensure HTML string is bytes with UTF-8 encoding
            if isinstance(html_cleaned, str):
                html_bytes = html_cleaned.encode('utf-8')
            else:
                html_bytes = html_cleaned

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

            logger.info(f"KPO PDF generated successfully with xhtml2pdf: {len(kpo_entries)} entries, firma={firma.naziv if firma else 'All'}")

            return pdf_bytes

        except Exception as xhtml_error:
            logger.error(f"Failed to generate KPO PDF: {xhtml_error}", exc_info=True)
            raise RuntimeError(f"PDF generation failed - WeasyPrint: {weasy_error}, xhtml2pdf: {xhtml_error}")
