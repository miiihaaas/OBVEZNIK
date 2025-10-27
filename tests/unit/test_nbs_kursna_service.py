"""Unit tests for NBS Kursna Lista Service."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from zeep.exceptions import Fault
from decimal import Decimal
from datetime import date, timedelta
import requests

from app.services import nbs_kursna_service


class TestNBSKursnaService:
    """Tests for NBS Kursna Lista SOAP API service."""

    @patch('app.services.nbs_kursna_service.Client')
    def test_fetch_kursna_lista_soap_success(self, mock_client_class, app):
        """Test successful SOAP API call to NBS."""
        with app.app_context():
            # Mock SOAP response XML
            xml_response = '''<?xml version="1.0" encoding="utf-8"?>
            <ExchangeRates xmlns="http://communicationoffice.nbs.rs">
                <ExchangeRate>
                    <CurrencyCode>EUR</CurrencyCode>
                    <MiddleRate>117,5432</MiddleRate>
                </ExchangeRate>
                <ExchangeRate>
                    <CurrencyCode>USD</CurrencyCode>
                    <MiddleRate>105,2341</MiddleRate>
                </ExchangeRate>
                <ExchangeRate>
                    <CurrencyCode>GBP</CurrencyCode>
                    <MiddleRate>135,6789</MiddleRate>
                </ExchangeRate>
                <ExchangeRate>
                    <CurrencyCode>CHF</CurrencyCode>
                    <MiddleRate>120,3456</MiddleRate>
                </ExchangeRate>
            </ExchangeRates>'''

            # Mock zeep Client
            mock_client = MagicMock()
            mock_client.service.GetCurrentExchangeRate.return_value = xml_response
            mock_client_class.return_value = mock_client

            # Call service function
            kursevi = nbs_kursna_service.fetch_kursna_lista_soap(date.today())

            # Assertions
            assert kursevi is not None
            assert kursevi['EUR'] == Decimal('117.5432')
            assert kursevi['USD'] == Decimal('105.2341')
            assert kursevi['GBP'] == Decimal('135.6789')
            assert kursevi['CHF'] == Decimal('120.3456')

    @patch('app.services.nbs_kursna_service.Client')
    def test_fetch_kursna_lista_soap_parse_error(self, mock_client_class, app):
        """Test handling of XML parsing error (invalid XML)."""
        with app.app_context():
            # Mock invalid XML response
            mock_client = MagicMock()
            mock_client.service.GetCurrentExchangeRate.return_value = 'invalid xml <>'
            mock_client_class.return_value = mock_client

            # Should raise exception on parse error
            with pytest.raises(Exception):
                nbs_kursna_service.fetch_kursna_lista_soap(date.today())

    @patch('app.services.nbs_kursna_service.Client')
    def test_fetch_kursna_lista_soap_auth_error(self, mock_client_class, app):
        """Test handling of SOAP authentication failure."""
        with app.app_context():
            # Mock SOAP Fault exception (auth error)
            mock_client = MagicMock()
            mock_client.service.GetCurrentExchangeRate.side_effect = Fault('Authentication failed')
            mock_client_class.return_value = mock_client

            # Should raise Fault exception
            with pytest.raises(Fault):
                nbs_kursna_service.fetch_kursna_lista_soap(date.today())

    @patch('app.services.nbs_kursna_service.Client')
    def test_fetch_kursna_lista_soap_timeout(self, mock_client_class, app):
        """Test handling of timeout error."""
        with app.app_context():
            # Mock timeout exception
            mock_client = MagicMock()
            mock_client.service.GetCurrentExchangeRate.side_effect = requests.Timeout('Connection timeout')
            mock_client_class.return_value = mock_client

            # Should raise Timeout exception
            with pytest.raises(requests.Timeout):
                nbs_kursna_service.fetch_kursna_lista_soap(date.today())

    @patch('app.services.nbs_kursna_service.Client')
    def test_fetch_kursna_lista_soap_connection_error(self, mock_client_class, app):
        """Test handling of connection error."""
        with app.app_context():
            # Mock connection error
            mock_client = MagicMock()
            mock_client.service.GetCurrentExchangeRate.side_effect = requests.ConnectionError('Cannot connect')
            mock_client_class.return_value = mock_client

            # Should raise ConnectionError exception
            with pytest.raises(requests.ConnectionError):
                nbs_kursna_service.fetch_kursna_lista_soap(date.today())

    def test_get_kurs_cache_hit(self, app):
        """Test get_kurs with cache hit."""
        with app.app_context():
            # Mock Redis cache hit
            redis_mock = Mock()
            redis_mock.get.return_value = b'117.5432'
            app.extensions['redis'] = redis_mock

            # Call service function
            kurs = nbs_kursna_service.get_kurs('EUR', date(2025, 1, 15))

            # Assertions
            assert kurs == Decimal('117.5432')
            redis_mock.get.assert_called_once_with('nbs_kurs_EUR_2025-01-15')

    @patch('app.services.nbs_kursna_service.fetch_kursna_lista_soap')
    def test_get_kurs_cache_miss_soap_success(self, mock_fetch, app):
        """Test get_kurs with cache miss and successful SOAP call."""
        with app.app_context():
            # Mock Redis cache miss
            redis_mock = Mock()
            redis_mock.get.return_value = None
            app.extensions['redis'] = redis_mock

            # Mock SOAP response
            mock_fetch.return_value = {
                'EUR': Decimal('117.5432'),
                'USD': Decimal('105.2341'),
                'GBP': Decimal('135.6789'),
                'CHF': Decimal('120.3456')
            }

            # Call service function
            kurs = nbs_kursna_service.get_kurs('EUR', date(2025, 1, 15))

            # Assertions
            assert kurs == Decimal('117.5432')
            mock_fetch.assert_called_once_with(date(2025, 1, 15))
            # Verify cache write
            redis_mock.setex.assert_called_once()

    @patch('app.services.nbs_kursna_service.fetch_kursna_lista_soap')
    def test_get_kurs_fallback_to_previous_day(self, mock_fetch, app):
        """Test get_kurs fallback to previous cached rate when SOAP fails."""
        with app.app_context():
            danas = date(2025, 1, 15)
            jucer = date(2025, 1, 14)

            # Mock Redis: cache miss for danas, hit for jucer
            redis_mock = Mock()

            def mock_get(key):
                if key == f'nbs_kurs_EUR_{danas}':
                    return None  # Cache miss for danas
                elif key == f'nbs_kurs_EUR_{jucer}':
                    return b'117.1234'  # Cache hit for jucer (fallback)
                return None

            redis_mock.get.side_effect = mock_get
            app.extensions['redis'] = redis_mock

            # Mock SOAP failure
            mock_fetch.side_effect = requests.Timeout('Connection timeout')

            # Call service function
            kurs = nbs_kursna_service.get_kurs('EUR', danas)

            # Assertions - should return fallback kurs from jucer
            assert kurs == Decimal('117.1234')
            mock_fetch.assert_called_once_with(danas)

    @patch('app.services.nbs_kursna_service.fetch_kursna_lista_soap')
    def test_get_kurs_no_fallback_available(self, mock_fetch, app):
        """Test get_kurs returns None when SOAP fails and no fallback cache exists."""
        with app.app_context():
            # Mock Redis: all cache misses
            redis_mock = Mock()
            redis_mock.get.return_value = None
            app.extensions['redis'] = redis_mock

            # Mock SOAP failure
            mock_fetch.side_effect = requests.Timeout('Connection timeout')

            # Call service function
            kurs = nbs_kursna_service.get_kurs('EUR', date(2025, 1, 15))

            # Assertions - should return None
            assert kurs is None

    def test_get_kurs_invalid_currency(self, app):
        """Test get_kurs with invalid currency code."""
        with app.app_context():
            redis_mock = Mock()
            app.extensions['redis'] = redis_mock

            # Call with invalid currency
            kurs = nbs_kursna_service.get_kurs('XXX', date(2025, 1, 15))

            # Should return None
            assert kurs is None

    def test_cache_kurs(self, app):
        """Test cache_kurs helper function."""
        with app.app_context():
            # Mock Redis
            redis_mock = Mock()
            app.extensions['redis'] = redis_mock

            # Call cache function
            nbs_kursna_service.cache_kurs('EUR', date(2025, 1, 15), Decimal('117.5432'))

            # Verify Redis setex was called correctly
            redis_mock.setex.assert_called_once_with(
                'nbs_kurs_EUR_2025-01-15',
                86400,  # 24h TTL
                '117.5432'
            )

    def test_cache_kurs_no_redis(self, app):
        """Test cache_kurs gracefully handles missing Redis client."""
        with app.app_context():
            # Disable Redis
            app.extensions['redis'] = None

            # Should not crash
            nbs_kursna_service.cache_kurs('EUR', date(2025, 1, 15), Decimal('117.5432'))

    def test_parse_xml_kursna_lista_empty(self, app):
        """Test _parse_xml_kursna_lista with empty string."""
        with app.app_context():
            result = nbs_kursna_service._parse_xml_kursna_lista('')
            assert result == {}

            result = nbs_kursna_service._parse_xml_kursna_lista(None)
            assert result == {}

    def test_parse_xml_kursna_lista_no_exchange_rates(self, app):
        """Test _parse_xml_kursna_lista with XML missing ExchangeRate elements."""
        with app.app_context():
            xml_response = '''<?xml version="1.0"?><root></root>'''
            result = nbs_kursna_service._parse_xml_kursna_lista(xml_response)
            assert result == {}

    def test_parse_xml_kursna_lista_partial_currencies(self, app):
        """Test _parse_xml_kursna_lista with only some currencies present."""
        with app.app_context():
            xml_response = '''<?xml version="1.0" encoding="utf-8"?>
            <ExchangeRates xmlns="http://communicationoffice.nbs.rs">
                <ExchangeRate>
                    <CurrencyCode>EUR</CurrencyCode>
                    <MiddleRate>117,5432</MiddleRate>
                </ExchangeRate>
                <ExchangeRate>
                    <CurrencyCode>JPY</CurrencyCode>
                    <MiddleRate>0,7123</MiddleRate>
                </ExchangeRate>
            </ExchangeRates>'''

            result = nbs_kursna_service._parse_xml_kursna_lista(xml_response)

            # Should only return EUR (JPY is not in supported list)
            assert len(result) == 1
            assert 'EUR' in result
            assert result['EUR'] == Decimal('117.5432')
            assert 'JPY' not in result

    def test_redis_failure_graceful_degradation(self, app):
        """Test that Redis failures don't crash get_kurs."""
        with app.app_context():
            # Mock Redis to raise exception
            redis_mock = Mock()
            redis_mock.get.side_effect = Exception('Redis connection error')
            app.extensions['redis'] = redis_mock

            # Should not crash, should continue with SOAP call
            with patch('app.services.nbs_kursna_service.fetch_kursna_lista_soap') as mock_fetch:
                mock_fetch.return_value = {
                    'EUR': Decimal('117.5432'),
                    'USD': Decimal('105.2341'),
                    'GBP': Decimal('135.6789'),
                    'CHF': Decimal('120.3456')
                }

                kurs = nbs_kursna_service.get_kurs('EUR', date(2025, 1, 15))

                # Should still work despite Redis failure
                assert kurs == Decimal('117.5432')
