"""NBS Kursna Lista service for fetching exchange rates via SOAP."""

from zeep import Client
from zeep import xsd
from zeep.exceptions import Fault
from zeep.transports import Transport
import xml.etree.ElementTree as ET
from typing import Dict, Optional
from decimal import Decimal
from datetime import date, timedelta
import json
from flask import current_app
import requests


def fetch_kursna_lista_soap(datum: date) -> Dict[str, Decimal]:
    """
    Fetch exchange rates from NBS CurrentExchangeRate SOAP API.

    Args:
        datum: Date for which to fetch exchange rates

    Returns:
        dict: Exchange rates for EUR, USD, GBP, CHF
        Example: {'EUR': Decimal('117.5432'), 'USD': Decimal('105.2341'), ...}

    Raises:
        Exception: If SOAP call fails
    """
    try:
        wsdl = "https://webservices.nbs.rs/CommunicationOfficeService1_0/CurrentExchangeRateXmlService.asmx?WSDL"

        # Configure transport with timeout
        transport = Transport(timeout=10)
        client = Client(wsdl, transport=transport)

        # Create SOAP auth header (reuse pattern from nbs_komitent_service.py)
        namespace = "http://communicationoffice.nbs.rs"
        auth_header = xsd.Element(
            f'{{{namespace}}}AuthenticationHeader',
            xsd.ComplexType([
                xsd.Element(f'{{{namespace}}}UserName', xsd.String()),
                xsd.Element(f'{{{namespace}}}Password', xsd.String()),
                xsd.Element(f'{{{namespace}}}LicenceID', xsd.String()),
            ])
        )
        auth_value = auth_header(
            UserName=current_app.config['NBS_USERNAME'],
            Password=current_app.config['NBS_PASSWORD'],
            LicenceID=current_app.config['NBS_LICENCE_ID']
        )

        # Call GetCurrentExchangeRate method
        xml_response = client.service.GetCurrentExchangeRate(
            _soapheaders=[auth_value]
        )

        # Parse XML response
        kursevi = _parse_xml_kursna_lista(xml_response)

        if not kursevi:
            raise ValueError("Failed to parse exchange rates from NBS response")

        current_app.logger.info(f"NBS SOAP API: kursna lista fetched for {datum}: {kursevi}")
        return kursevi

    except Fault as e:
        current_app.logger.error(f"NBS SOAP Fault for datum {datum}: {e}")
        raise
    except requests.Timeout:
        current_app.logger.error(f"NBS API timeout for datum {datum}")
        raise
    except requests.ConnectionError as e:
        current_app.logger.error(f"NBS API connection error for datum {datum}: {e}")
        raise
    except ET.ParseError as e:
        current_app.logger.error(f"NBS XML parsing error for datum {datum}: {e}")
        raise
    except Exception as e:
        current_app.logger.error(f"NBS API unexpected error for datum {datum}: {e}")
        raise


def _parse_xml_kursna_lista(xml_string: str) -> Dict[str, Decimal]:
    """
    Parse XML response from NBS and extract EUR, USD, GBP, CHF rates.

    Args:
        xml_string: XML response from NBS SOAP service

    Returns:
        dict: Parsed exchange rates for supported currencies
    """
    if not xml_string:
        return {}

    try:
        root = ET.fromstring(xml_string)
        kursevi = {}

        # Parse ExchangeRate elements (adjust XPath based on actual XML structure)
        # Namespace-aware search
        namespace = "http://communicationoffice.nbs.rs"

        # Try with namespace first
        exchange_rate_elements = root.findall(f'.//{{{namespace}}}ExchangeRate')

        # Fallback: try without namespace
        if not exchange_rate_elements:
            exchange_rate_elements = root.findall('.//ExchangeRate')

        for row in exchange_rate_elements:
            # Extract currency code (try with namespace first, then without)
            valuta_elem = row.find(f'{{{namespace}}}CurrencyCode')
            if valuta_elem is None:
                valuta_elem = row.find('CurrencyCode')

            if valuta_elem is None or not valuta_elem.text:
                continue

            valuta = valuta_elem.text
            if valuta not in ['EUR', 'USD', 'GBP', 'CHF']:
                continue

            # Extract middle rate (try with namespace first, then without)
            kurs_elem = row.find(f'{{{namespace}}}MiddleRate')
            if kurs_elem is None:
                kurs_elem = row.find('MiddleRate')

            if kurs_elem is None or not kurs_elem.text:
                current_app.logger.warning(f"MiddleRate not found for {valuta}")
                continue

            # Convert comma to dot for decimal parsing
            kurs_value = kurs_elem.text.replace(',', '.')
            kursevi[valuta] = Decimal(kurs_value)

        return kursevi

    except Exception as e:
        current_app.logger.error(f"XML parsing error: {e}")
        return {}


def get_kurs(valuta: str, datum: date) -> Optional[Decimal]:
    """
    Get exchange rate for a specific currency and date.

    Checks Redis cache first. If cache miss, fetches from NBS SOAP API.
    If SOAP call fails, falls back to previous cached rates (up to 7 days).

    Args:
        valuta: Currency code (EUR, USD, GBP, CHF)
        datum: Date for exchange rate

    Returns:
        Decimal: Exchange rate or None if not available
    """
    # Validate currency
    if valuta not in ['EUR', 'USD', 'GBP', 'CHF']:
        current_app.logger.warning(f"Invalid currency: {valuta}")
        return None

    # Check Redis cache
    redis_client = current_app.extensions.get('redis')
    if redis_client:
        cache_key = f"nbs_kurs_{valuta}_{datum}"
        try:
            cached_kurs = redis_client.get(cache_key)
            if cached_kurs:
                current_app.logger.info(f"Cache hit for {cache_key}")
                return Decimal(cached_kurs.decode('utf-8'))
        except Exception as e:
            current_app.logger.warning(f"Redis cache read error: {e}")

    # Cache miss - fetch from NBS SOAP API
    try:
        kursevi = fetch_kursna_lista_soap(datum)
        kurs = kursevi.get(valuta)

        if kurs:
            # Cache the result (24h TTL)
            cache_kurs(valuta, datum, kurs)
            return kurs
        else:
            current_app.logger.warning(f"Currency {valuta} not found in NBS response for {datum}")
            return None

    except Exception as e:
        # SOAP call failed - try fallback to previous cached rates
        current_app.logger.warning(f"NBS SOAP call failed, trying fallback: {e}")

        if redis_client:
            # Try up to 7 days back
            for days_back in range(1, 8):
                fallback_datum = datum - timedelta(days=days_back)
                fallback_key = f"nbs_kurs_{valuta}_{fallback_datum}"

                try:
                    cached_kurs = redis_client.get(fallback_key)
                    if cached_kurs:
                        current_app.logger.warning(
                            f"Using cached kurs from {fallback_datum} as fallback for {datum}"
                        )
                        return Decimal(cached_kurs.decode('utf-8'))
                except Exception as cache_err:
                    current_app.logger.warning(f"Fallback cache read error: {cache_err}")
                    continue

        # No cached rates available
        current_app.logger.error(f"No cached kurs available for {valuta} on {datum}")
        return None


def cache_kurs(valuta: str, datum: date, kurs: Decimal) -> None:
    """
    Cache exchange rate in Redis.

    Args:
        valuta: Currency code
        datum: Date for exchange rate
        kurs: Exchange rate value
    """
    redis_client = current_app.extensions.get('redis')
    if not redis_client:
        current_app.logger.warning("Redis client not available, skipping cache")
        return

    cache_key = f"nbs_kurs_{valuta}_{datum}"

    try:
        # Store as string with 24h TTL (86400 seconds)
        redis_client.setex(cache_key, 86400, str(kurs))
        current_app.logger.info(f"Cached {cache_key} = {kurs}")
    except Exception as e:
        current_app.logger.warning(f"Redis cache write error: {e}")
