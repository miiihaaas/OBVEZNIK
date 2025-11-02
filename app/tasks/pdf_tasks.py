"""Celery tasks for PDF generation."""

from flask import current_app
from app import db
from app.models import Faktura
from app.services import pdf_service


def generate_faktura_pdf_task(faktura_id):
    """
    Celery task to generate PDF for a faktura in background.

    Args:
        faktura_id: ID of the Faktura to generate PDF for

    Returns:
        dict: Status dict with 'status', 'faktura_id', and optional 'pdf_url' or 'error'
    """
    try:
        # Fetch faktura from database
        faktura = Faktura.query.get(faktura_id)

        if not faktura:
            current_app.logger.error(f"Faktura {faktura_id} not found")
            return {
                'status': 'error',
                'faktura_id': faktura_id,
                'error': 'Faktura not found'
            }

        # Update status to 'generating'
        faktura.status_pdf = 'generating'
        db.session.commit()

        # Generate PDF
        pdf_bytes = pdf_service.generate_pdf(faktura)

        # Save PDF to disk
        pdf_path = pdf_service.save_pdf(pdf_bytes, faktura)

        current_app.logger.info(
            f"PDF generated successfully for Faktura {faktura_id}: {pdf_path}"
        )

        return {
            'status': 'success',
            'faktura_id': faktura_id,
            'pdf_url': pdf_path
        }

    except Exception as e:
        current_app.logger.error(
            f"PDF generation failed for Faktura {faktura_id}: {e}"
        )

        # Update status to 'failed' in database
        try:
            faktura = Faktura.query.get(faktura_id)
            if faktura:
                faktura.status_pdf = 'failed'
                db.session.commit()
        except Exception as db_error:
            current_app.logger.error(
                f"Failed to update Faktura {faktura_id} status to 'failed': {db_error}"
            )

        return {
            'status': 'error',
            'faktura_id': faktura_id,
            'error': str(e)
        }
