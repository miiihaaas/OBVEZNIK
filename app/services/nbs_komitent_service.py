"""NBS Komitent API service for fetching company data via SOAP."""

from zeep import Client
from zeep import xsd
from zeep.exceptions import Fault
from zeep.transports import Transport
import xml.etree.ElementTree as ET
from typing import Dict, Optional
import json
from flask import current_app
import requests


def fetch_company_by_pib(pib: str) -> Optional[Dict]:
    """
    Fetch company data from NBS Komitent API by PIB (SOAP).

    Args:
        pib: PIB (8 or 9 digits)

    Returns:
        dict: Company data if found, None otherwise
        Example: {
            'naziv': '...',
            'adresa': '...',
            'broj': '...',
            'mesto': '...',
            'maticni_broj': '...',
            'source': 'nbs'
        }
    """
    # Validate PIB format (8 or 9 digits)
    if not pib or len(pib) not in [8, 9] or not pib.isdigit():
        current_app.logger.warning(f"Invalid PIB format: {pib}")
        return None

    # Check Redis cache first
    redis_client = current_app.extensions.get('redis')
    if redis_client:
        cache_key = f"nbs:company:{pib}"
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                current_app.logger.info(f"NBS cache hit for PIB: {pib}")
                return json.loads(cached_data)
        except Exception as e:
            current_app.logger.warning(f"Redis cache read error: {e}")

    # Call NBS SOAP API
    try:
        wsdl_core = "https://webservices.nbs.rs/CommunicationOfficeService1_0/CoreXmlService.asmx?WSDL"

        # Configure transport with timeout
        transport = Transport(timeout=10)
        client = Client(wsdl_core, transport=transport)

        # Create SOAP auth header
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

        # Call GetCompany method
        xml_response = client.service.GetCompany(
            companyID='00000000-0000-0000-0000-000000000000',
            companyCode=0,
            name='',
            city='',
            nationalIdentificationNumber=0,
            taxIdentificationNumber=int(pib),
            startItemNumber=0,
            endItemNumber=0,
            _soapheaders=[auth_value]
        )

        # Parse XML response
        firma_data = _parse_xml_response(xml_response)

        if not firma_data:
            current_app.logger.info(f"NBS API: PIB {pib} not found")
            return None

        # Cache response (24h TTL)
        if redis_client and firma_data:
            try:
                redis_client.setex(cache_key, 86400, json.dumps(firma_data))
            except Exception as e:
                current_app.logger.warning(f"Redis cache write error: {e}")

        current_app.logger.info(f"NBS API success for PIB: {pib}")
        return firma_data

    except Fault as e:
        current_app.logger.warning(f"NBS SOAP Fault for PIB {pib}: {e}")
        return None
    except requests.Timeout:
        current_app.logger.warning(f"NBS API timeout for PIB {pib}")
        return None
    except requests.ConnectionError as e:
        current_app.logger.warning(f"NBS API connection error for PIB {pib}: {e}")
        return None
    except ET.ParseError as e:
        current_app.logger.warning(f"NBS XML parsing error for PIB {pib}: {e}")
        return None
    except Exception as e:
        current_app.logger.error(f"NBS API unexpected error for PIB {pib}: {e}")
        return None


def _parse_xml_response(xml_string: str) -> Optional[Dict]:
    """
    Parse XML response from NBS API into dictionary.

    Args:
        xml_string: XML response from NBS SOAP service

    Returns:
        dict: Parsed company data or None if parsing fails
    """
    if not xml_string:
        return None

    try:
        root = ET.fromstring(xml_string)

        # Navigate to Company element (namespace-aware)
        # NBS response structure: <Company>...</Company>
        company_element = root.find('.//{http://communicationoffice.nbs.rs}Company')

        if company_element is None:
            # Try without namespace
            company_element = root.find('.//Company')

        if company_element is None:
            return None

        # Extract company data
        def get_text(element, tag):
            """Helper to extract text from XML element."""
            child = element.find(f'.//{{{namespace}}}{tag}') if namespace else element.find(f'.//{tag}')
            if child is None:
                child = element.find(f'.//{tag}')
            return child.text.strip() if child is not None and child.text else ''

        namespace = "http://communicationoffice.nbs.rs"

        naziv = get_text(company_element, 'Name') or get_text(company_element, 'ShortName')
        adresa_raw = get_text(company_element, 'Address')
        mesto = get_text(company_element, 'City')
        maticni_broj = get_text(company_element, 'NationalIdentificationNumber')

        # Parse adresa (try to split street and number)
        # NBS format is usually "Ulica Broj", e.g., "Kneza Miloša 12"
        adresa = adresa_raw
        broj = ''
        if adresa_raw:
            parts = adresa_raw.rsplit(' ', 1)
            if len(parts) == 2 and parts[1].replace('-', '').replace('/', '').replace('a', '').replace('b', '').isdigit():
                adresa = parts[0]
                broj = parts[1]
            else:
                adresa = adresa_raw
                broj = 'bb'  # bez broja

        return {
            'naziv': naziv,
            'adresa': adresa,
            'broj': broj,
            'mesto': mesto,
            'maticni_broj': maticni_broj,
            'source': 'nbs'
        }

    except Exception as e:
        current_app.logger.error(f"XML parsing error: {e}")
        return None
