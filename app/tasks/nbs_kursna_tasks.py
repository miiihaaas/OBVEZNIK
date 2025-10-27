"""Celery tasks for NBS Kursna Lista operations."""

from datetime import date
from flask import current_app


def update_daily_kursna_lista():
    """
    Celery task to update daily exchange rates from NBS SOAP API.

    Fetches exchange rates for EUR, USD, GBP, CHF and caches them in Redis.
    Scheduled to run daily at 14:00 (after NBS publishes the daily rates).
    """
    from app.services.nbs_kursna_service import fetch_kursna_lista_soap, cache_kurs

    today = date.today()

    try:
        # Fetch kursna lista from NBS SOAP API
        kursevi = fetch_kursna_lista_soap(today)

        # Cache each currency rate in Redis
        for valuta, kurs in kursevi.items():
            cache_kurs(valuta, today, kurs)

        current_app.logger.info(
            f"NBS kursna lista updated for {today}: {kursevi}"
        )

        return {
            'status': 'success',
            'datum': str(today),
            'kursevi': {valuta: str(kurs) for valuta, kurs in kursevi.items()}
        }

    except Exception as e:
        current_app.logger.error(
            f"Failed to update NBS kursna lista for {today}: {e}"
        )

        return {
            'status': 'error',
            'datum': str(today),
            'error': str(e)
        }
