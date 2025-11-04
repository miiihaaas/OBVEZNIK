"""
Email service for sending invoices via SMTP.
Handles email sending with PDF attachments using Flask-Mail.
"""
import os
from flask import current_app, render_template
from flask_mail import Message
from app import mail


class EmailError(Exception):
    """Base exception for email-related errors."""
    pass


class InvalidEmailError(EmailError):
    """Raised when email format is invalid."""
    pass


class SMTPError(EmailError):
    """Raised when SMTP sending fails."""
    pass


def send_faktura_email(faktura, recipient_email, cc_email=None, custom_subject=None, custom_body=None):
    """
    Send invoice email with PDF attachment.

    Args:
        faktura: Faktura model instance
        recipient_email: Email address of the recipient
        cc_email: Optional CC email address
        custom_subject: Custom subject line (overrides default)
        custom_body: Custom email body HTML (overrides template)

    Returns:
        bool: True if email was sent successfully

    Raises:
        InvalidEmailError: If email format is invalid
        FileNotFoundError: If PDF file is not generated
        SMTPError: If SMTP sending fails
    """
    # Validate that PDF exists
    if not faktura.pdf_url:
        raise FileNotFoundError(f"PDF nije generisan za fakturu {faktura.broj_fakture}")

    # Construct absolute path for PDF
    pdf_path = faktura.pdf_url
    if not os.path.isabs(pdf_path):
        # If relative path, make it absolute relative to app root
        pdf_path = os.path.join(current_app.root_path, '..', pdf_path)

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF fajl ne postoji: {pdf_path}")

    # Generate subject and body
    subject = custom_subject or generate_email_subject(faktura)
    body_html = custom_body or get_email_template(faktura)

    # Generate plain text fallback
    body_text = generate_plain_text_body(faktura)

    # Create email message
    msg = Message(
        subject=subject,
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[recipient_email]
    )

    # Add CC if provided
    if cc_email:
        msg.cc = [cc_email]

    # Set both plain text and HTML body (for better email client compatibility)
    msg.body = body_text  # Plain text fallback
    msg.html = body_html  # HTML version (preferred)

    # Attach PDF
    with open(pdf_path, 'rb') as pdf_file:
        pdf_filename = f"Faktura_{faktura.broj_fakture}.pdf"
        msg.attach(
            filename=pdf_filename,
            content_type="application/pdf",
            data=pdf_file.read()
        )

    # Send email
    try:
        mail.send(msg)
        current_app.logger.info(
            f"Email poslat za fakturu {faktura.broj_fakture} na {recipient_email}"
        )
        return True
    except Exception as exc:
        current_app.logger.error(
            f"SMTP greška pri slanju email-a za fakturu {faktura.broj_fakture}: {str(exc)}"
        )
        raise SMTPError(f"Slanje email-a neuspešno: {str(exc)}") from exc


def generate_email_subject(faktura, custom_subject=None):
    """
    Generate email subject line.

    Args:
        faktura: Faktura model instance
        custom_subject: Custom subject (overrides default)

    Returns:
        str: Email subject line
    """
    if custom_subject:
        return custom_subject

    return f"Faktura {faktura.broj_fakture} od {faktura.firma.naziv}"


def get_email_template(faktura, custom_body=None):
    """
    Get email template HTML based on invoice language.

    Args:
        faktura: Faktura model instance
        custom_body: Custom body HTML (overrides template)

    Returns:
        str: Email body HTML
    """
    if custom_body:
        return custom_body

    # Select template based on invoice language
    if faktura.jezik == 'en':
        template = 'fakture/email/faktura_en.html'
    else:
        template = 'fakture/email/faktura_sr.html'

    return render_template(template, faktura=faktura)


def generate_plain_text_body(faktura):
    """
    Generate plain text email body for email clients that don't support HTML.

    Args:
        faktura: Faktura model instance

    Returns:
        str: Plain text email body
    """
    if faktura.jezik == 'en':
        # English version
        text = f"""Dear Sir/Madam,

Please find attached invoice {faktura.broj_fakture} for services rendered/goods sold.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INVOICE DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Invoice Number:    {faktura.broj_fakture}
Invoice Date:      {faktura.datum_prometa.strftime('%d/%m/%Y')}
Due Date:          {faktura.datum_dospeca.strftime('%d/%m/%Y')}"""

        if faktura.poziv_na_broj:
            text += f"\nReference Number:  {faktura.poziv_na_broj}"

        if faktura.ukupan_iznos_originalna_valuta:
            text += f"\n\nTOTAL AMOUNT:      {faktura.ukupan_iznos_originalna_valuta:.2f} {faktura.valuta_fakture}"
            text += f"\n                   ({faktura.ukupan_iznos_rsd:.2f} RSD)"
        else:
            text += f"\n\nTOTAL AMOUNT:      {faktura.ukupan_iznos_rsd:.2f} RSD"

        text += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please arrange payment by the due date.

Thank you for your business.

Best regards,
{faktura.firma.naziv}
"""
    else:
        # Serbian version
        text = f"""Poštovani,

U prilogu vam šaljemo fakturu {faktura.broj_fakture} za izvršene usluge/prodate proizvode.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DETALJI FAKTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Broj fakture:      {faktura.broj_fakture}
Datum prometa:     {faktura.datum_prometa.strftime('%d.%m.%Y')}
Datum dospeća:     {faktura.datum_dospeca.strftime('%d.%m.%Y')}"""

        if faktura.poziv_na_broj:
            text += f"\nPoziv na broj:     {faktura.poziv_na_broj}"

        text += f"\n\nUKUPAN IZNOS:      {faktura.ukupan_iznos_rsd:.2f} RSD"

        text += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Molimo vas da izvršite uplatu u navedenom roku.

Hvala vam na saradnji i poverenju.

Srdačan pozdrav,
{faktura.firma.naziv}
"""

    # Add contact info if available
    if faktura.firma.email or faktura.firma.telefon:
        text += "\n"
        if faktura.firma.email:
            text += f"Email: {faktura.firma.email}\n"
        if faktura.firma.telefon:
            text += f"Telefon: {faktura.firma.telefon}\n"

    text += "\n---\nOvaj email je automatski generisan iz sistema OBVEZNIK.\nPDF faktura je priložena uz ovaj email.\n"

    return text


def validate_email_format(email):
    """
    Validate email format.

    Args:
        email: Email address string

    Returns:
        bool: True if valid

    Raises:
        InvalidEmailError: If email format is invalid
    """
    import re

    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(pattern, email):
        raise InvalidEmailError(f"Nevalidan email format: {email}")

    return True
