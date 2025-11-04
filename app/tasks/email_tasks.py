"""Celery tasks for email sending."""

from datetime import datetime
from flask import current_app
from app import db
from app.models import Faktura
from app.services import email_service


def send_faktura_email_task(self, faktura_id, recipient_email, cc_email=None, custom_subject=None, custom_body=None):
    """
    Celery task to send invoice email in background with retry logic.

    This function is registered as a Celery task in celery_worker.py with:
    - max_retries=3
    - default_retry_delay=30 (exponential backoff: 30s, 60s, 120s)

    Args:
        self: Celery task instance (bound task)
        faktura_id: ID of the Faktura to send
        recipient_email: Email address of the recipient
        cc_email: Optional CC email address
        custom_subject: Custom subject line (overrides default)
        custom_body: Custom email body HTML (overrides template)

    Returns:
        dict: Status dict with 'status', 'faktura_id', and optional 'error'

    Raises:
        Exception: Retries on failure with exponential backoff (30s, 60s, 120s)
    """
    try:
        # Fetch faktura from database
        faktura = Faktura.query.get(faktura_id)

        if not faktura:
            error_msg = f"Faktura {faktura_id} not found"
            current_app.logger.error(error_msg)
            # Don't retry if faktura doesn't exist
            return {
                'status': 'error',
                'faktura_id': faktura_id,
                'error': error_msg
            }

        # Validate email format
        try:
            email_service.validate_email_format(recipient_email)
            if cc_email:
                email_service.validate_email_format(cc_email)
        except email_service.InvalidEmailError as e:
            current_app.logger.error(f"Invalid email format: {e}")
            faktura.email_status = 'failed'
            faktura.email_error_message = str(e)
            db.session.commit()
            # Don't retry on validation errors
            return {
                'status': 'error',
                'faktura_id': faktura_id,
                'error': str(e)
            }

        # Send email
        email_service.send_faktura_email(
            faktura,
            recipient_email,
            cc_email,
            custom_subject,
            custom_body
        )

        # Update status to 'sent'
        faktura.email_status = 'sent'
        faktura.email_sent_at = datetime.now()
        faktura.email_recipient = recipient_email
        faktura.email_error_message = None
        db.session.commit()

        current_app.logger.info(
            f"Email sent successfully for Faktura {faktura_id} to {recipient_email}"
        )

        return {
            'status': 'success',
            'faktura_id': faktura_id,
            'recipient_email': recipient_email
        }

    except (email_service.SMTPError, ConnectionError, TimeoutError) as e:
        # Retry on transient errors (SMTP, network issues)
        current_app.logger.warning(
            f"Email sending failed for Faktura {faktura_id} (attempt {self.request.retries + 1}/3): {e}"
        )

        # Update status to 'failed' in database
        try:
            faktura = Faktura.query.get(faktura_id)
            if faktura:
                faktura.email_status = 'failed'
                faktura.email_error_message = f"Attempt {self.request.retries + 1}: {str(e)}"
                db.session.commit()
        except Exception as db_error:
            current_app.logger.error(
                f"Failed to update Faktura {faktura_id} email status: {db_error}"
            )

        # Retry with exponential backoff: 30s, 60s, 120s
        # Countdown = base_delay * (2 ^ retry_count)
        retry_delay = 30 * (2 ** self.request.retries)

        # Raise for retry (Celery will catch and retry)
        raise self.retry(exc=e, countdown=retry_delay)

    except Exception as e:
        # Non-retryable errors (e.g., file not found, invalid data)
        current_app.logger.error(
            f"Email sending failed permanently for Faktura {faktura_id}: {e}"
        )

        # Update status to 'failed' in database
        try:
            faktura = Faktura.query.get(faktura_id)
            if faktura:
                faktura.email_status = 'failed'
                faktura.email_error_message = str(e)
                db.session.commit()
        except Exception as db_error:
            current_app.logger.error(
                f"Failed to update Faktura {faktura_id} email status to 'failed': {db_error}"
            )

        return {
            'status': 'error',
            'faktura_id': faktura_id,
            'error': str(e)
        }
