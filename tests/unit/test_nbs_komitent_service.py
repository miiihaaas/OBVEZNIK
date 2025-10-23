"""Unit tests for NBS Komitent Service."""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from zeep.exceptions import Fault
import xml.etree.ElementTree as ET
import requests

from app.services import nbs_komitent_service


class TestNBSKomitentService:
    """Tests for NBS Komitent SOAP API service."""

    def test_fetch_company_by_pib_invalid_format(self, app):
        """Test that invalid PIB format returns None."""
        with app.app_context():
            # Test short PIB
            result = nbs_komitent_service.fetch_company_by_pib('1234567')
            assert result is None

            # Test long PIB
            result = nbs_komitent_service.fetch_company_by_pib('123456789')
            assert result is None

            # Test non-numeric PIB
            result = nbs_komitent_service.fetch_company_by_pib('1234567a')
            assert result is None

            # Test empty PIB
            result = nbs_komitent_service.fetch_company_by_pib('')
            assert result is None

    def test_fetch_company_by_pib_cache_hit(self, app, mocker):
        """Test that cached data is returned when available."""
        with app.app_context():
            # Mock Redis cache hit
            mock_redis = mocker.patch.object(app.extensions, 'get')
            cached_data = {
                'naziv': 'Test Firma',
                'adresa': 'Kneza Miloša',
                'broj': '12',
                'mesto': 'Beograd',
                'maticni_broj': '87654321',
                'source': 'nbs'
            }

            # Setup Redis mock
            redis_mock = Mock()
            redis_mock.get.return_value = json.dumps(cached_data).encode('utf-8')
            app.extensions['redis'] = redis_mock

            result = nbs_komitent_service.fetch_company_by_pib('12345678')

            assert result is not None
            assert result['naziv'] == 'Test Firma'
            assert result['adresa'] == 'Kneza Miloša'
            assert result['source'] == 'nbs'
            redis_mock.get.assert_called_once_with('nbs:company:12345678')

    @patch('app.services.nbs_komitent_service.Client')
    def test_fetch_company_by_pib_success(self, mock_client_class, app):
        """Test successful NBS API call and XML parsing."""
        with app.app_context():
            # Disable Redis for this test
            app.extensions['redis'] = None

            # Mock SOAP response XML
            xml_response = '''<?xml version="1.0"?>
            <root xmlns="http://communicationoffice.nbs.rs">
                <Company>
                    <Name>Marimar Trade DOO</Name>
                    <ShortName>Marimar</ShortName>
                    <NationalIdentificationNumber>12345678</NationalIdentificationNumber>
                    <Address>Kneza Miloša 12</Address>
                    <City>Beograd</City>
                </Company>
            </root>'''

            # Mock zeep Client
            mock_client = MagicMock()
            mock_client.service.GetCompany.return_value = xml_response
            mock_client_class.return_value = mock_client

            result = nbs_komitent_service.fetch_company_by_pib('12345678')

            assert result is not None
            assert result['naziv'] == 'Marimar Trade DOO'
            assert result['maticni_broj'] == '12345678'
            assert result['adresa'] == 'Kneza Miloša'
            assert result['broj'] == '12'
            assert result['mesto'] == 'Beograd'
            assert result['source'] == 'nbs'

    @patch('app.services.nbs_komitent_service.Client')
    def test_fetch_company_by_pib_soap_fault(self, mock_client_class, app):
        """Test handling of SOAP Fault (PIB not found)."""
        with app.app_context():
            # Disable Redis
            app.extensions['redis'] = None

            # Mock SOAP Fault exception
            mock_client = MagicMock()
            mock_client.service.GetCompany.side_effect = Fault('PIB not found')
            mock_client_class.return_value = mock_client

            result = nbs_komitent_service.fetch_company_by_pib('12345678')

            assert result is None

    @patch('app.services.nbs_komitent_service.Client')
    def test_fetch_company_by_pib_timeout(self, mock_client_class, app):
        """Test handling of timeout error."""
        with app.app_context():
            # Disable Redis
            app.extensions['redis'] = None

            # Mock timeout exception
            mock_client = MagicMock()
            mock_client.service.GetCompany.side_effect = requests.Timeout('Connection timeout')
            mock_client_class.return_value = mock_client

            result = nbs_komitent_service.fetch_company_by_pib('12345678')

            assert result is None

    @patch('app.services.nbs_komitent_service.Client')
    def test_fetch_company_by_pib_connection_error(self, mock_client_class, app):
        """Test handling of connection error."""
        with app.app_context():
            # Disable Redis
            app.extensions['redis'] = None

            # Mock connection error
            mock_client = MagicMock()
            mock_client.service.GetCompany.side_effect = requests.ConnectionError('Cannot connect')
            mock_client_class.return_value = mock_client

            result = nbs_komitent_service.fetch_company_by_pib('12345678')

            assert result is None

    @patch('app.services.nbs_komitent_service.Client')
    def test_fetch_company_by_pib_xml_parse_error(self, mock_client_class, app):
        """Test handling of XML parsing error."""
        with app.app_context():
            # Disable Redis
            app.extensions['redis'] = None

            # Mock invalid XML response
            mock_client = MagicMock()
            mock_client.service.GetCompany.return_value = 'invalid xml <>'
            mock_client_class.return_value = mock_client

            result = nbs_komitent_service.fetch_company_by_pib('12345678')

            # Should return None on parse error
            assert result is None

    @patch('app.services.nbs_komitent_service.Client')
    def test_fetch_company_by_pib_cache_write(self, mock_client_class, app):
        """Test that successful response is cached."""
        with app.app_context():
            # Setup Redis mock
            redis_mock = Mock()
            redis_mock.get.return_value = None  # Cache miss
            app.extensions['redis'] = redis_mock

            # Mock SOAP response
            xml_response = '''<?xml version="1.0"?>
            <root xmlns="http://communicationoffice.nbs.rs">
                <Company>
                    <Name>Test Firma</Name>
                    <NationalIdentificationNumber>12345678</NationalIdentificationNumber>
                    <Address>Test Adresa 5</Address>
                    <City>Beograd</City>
                </Company>
            </root>'''

            mock_client = MagicMock()
            mock_client.service.GetCompany.return_value = xml_response
            mock_client_class.return_value = mock_client

            result = nbs_komitent_service.fetch_company_by_pib('12345678')

            assert result is not None
            # Verify Redis cache write was called
            redis_mock.setex.assert_called_once()
            call_args = redis_mock.setex.call_args
            assert call_args[0][0] == 'nbs:company:12345678'  # Cache key
            assert call_args[0][1] == 86400  # TTL 24h

    def test_parse_xml_response_empty(self, app):
        """Test _parse_xml_response with empty string."""
        with app.app_context():
            result = nbs_komitent_service._parse_xml_response('')
            assert result is None

            result = nbs_komitent_service._parse_xml_response(None)
            assert result is None

    def test_parse_xml_response_no_company_element(self, app):
        """Test _parse_xml_response with XML missing Company element."""
        with app.app_context():
            xml_response = '''<?xml version="1.0"?><root></root>'''
            result = nbs_komitent_service._parse_xml_response(xml_response)
            assert result is None

    def test_redis_failure_graceful_degradation(self, app, mocker):
        """Test that Redis failures don't crash the application."""
        with app.app_context():
            # Mock Redis to raise exception
            redis_mock = Mock()
            redis_mock.get.side_effect = Exception('Redis connection error')
            app.extensions['redis'] = redis_mock

            # Should not crash, should continue with API call
            with patch('app.services.nbs_komitent_service.Client') as mock_client_class:
                xml_response = '''<?xml version="1.0"?>
                <root xmlns="http://communicationoffice.nbs.rs">
                    <Company>
                        <Name>Test</Name>
                        <NationalIdentificationNumber>12345678</NationalIdentificationNumber>
                        <Address>Adresa 1</Address>
                        <City>Beograd</City>
                    </Company>
                </root>'''

                mock_client = MagicMock()
                mock_client.service.GetCompany.return_value = xml_response
                mock_client_class.return_value = mock_client

                result = nbs_komitent_service.fetch_company_by_pib('12345678')

                # Should still work despite Redis failure
                assert result is not None
                assert result['naziv'] == 'Test'
