"""Integration tests for NBS Kursna Lista Celery tasks."""
import pytest
from unittest.mock import patch, Mock
from decimal import Decimal
from datetime import date
import requests
from zeep.exceptions import Fault

from app.tasks.nbs_kursna_tasks import update_daily_kursna_lista


class TestNBSKursnaTasks:
    """Integration tests for NBS Kursna Lista Celery tasks."""

    @patch('app.services.nbs_kursna_service.fetch_kursna_lista_soap')
    def test_update_daily_kursna_lista_success(self, mock_fetch, app):
        """Test successful daily kursna lista update."""
        with app.app_context():
            # Mock Redis
            redis_mock = Mock()
            app.extensions['redis'] = redis_mock

            # Mock SOAP response
            mock_kursevi = {
                'EUR': Decimal('117.5432'),
                'USD': Decimal('105.2341'),
                'GBP': Decimal('135.6789'),
                'CHF': Decimal('120.3456')
            }
            mock_fetch.return_value = mock_kursevi

            # Call task
            result = update_daily_kursna_lista()

            # Assertions
            assert result['status'] == 'success'
            assert result['datum'] == str(date.today())
            assert 'EUR' in result['kursevi']
            assert result['kursevi']['EUR'] == '117.5432'

            # Verify SOAP was called
            mock_fetch.assert_called_once_with(date.today())

            # Verify Redis cache writes (4 currencies)
            assert redis_mock.setex.call_count == 4

    @patch('app.services.nbs_kursna_service.fetch_kursna_lista_soap')
    def test_update_daily_kursna_lista_soap_failure(self, mock_fetch, app):
        """Test handling of SOAP timeout during daily update."""
        with app.app_context():
            # Mock Redis
            redis_mock = Mock()
            app.extensions['redis'] = redis_mock

            # Mock SOAP timeout
            mock_fetch.side_effect = requests.Timeout('Connection timeout')

            # Call task
            result = update_daily_kursna_lista()

            # Assertions
            assert result['status'] == 'error'
            assert result['datum'] == str(date.today())
            assert 'error' in result

            # Verify SOAP was called
            mock_fetch.assert_called_once_with(date.today())

            # Verify no cache writes occurred
            redis_mock.setex.assert_not_called()

    @patch('app.services.nbs_kursna_service.fetch_kursna_lista_soap')
    def test_update_daily_kursna_lista_auth_error(self, mock_fetch, app):
        """Test handling of authentication failure during daily update."""
        with app.app_context():
            # Mock Redis
            redis_mock = Mock()
            app.extensions['redis'] = redis_mock

            # Mock SOAP auth error
            mock_fetch.side_effect = Fault('Authentication failed')

            # Call task
            result = update_daily_kursna_lista()

            # Assertions
            assert result['status'] == 'error'
            assert result['datum'] == str(date.today())
            assert 'error' in result

            # Verify SOAP was called
            mock_fetch.assert_called_once_with(date.today())

            # Verify no cache writes occurred
            redis_mock.setex.assert_not_called()

    @patch('app.services.nbs_kursna_service.fetch_kursna_lista_soap')
    def test_update_daily_kursna_lista_partial_failure(self, mock_fetch, app):
        """Test handling when only some currencies are returned."""
        with app.app_context():
            # Mock Redis
            redis_mock = Mock()
            app.extensions['redis'] = redis_mock

            # Mock SOAP response with only 2 currencies
            mock_kursevi = {
                'EUR': Decimal('117.5432'),
                'USD': Decimal('105.2341')
            }
            mock_fetch.return_value = mock_kursevi

            # Call task
            result = update_daily_kursna_lista()

            # Assertions
            assert result['status'] == 'success'
            assert 'EUR' in result['kursevi']
            assert 'USD' in result['kursevi']
            assert len(result['kursevi']) == 2

            # Verify only 2 cache writes
            assert redis_mock.setex.call_count == 2

    @patch('app.services.nbs_kursna_service.fetch_kursna_lista_soap')
    def test_update_daily_kursna_lista_redis_failure_graceful(self, mock_fetch, app):
        """Test that Redis write failures don't crash the task."""
        with app.app_context():
            # Mock Redis with write failure
            redis_mock = Mock()
            redis_mock.setex.side_effect = Exception('Redis write error')
            app.extensions['redis'] = redis_mock

            # Mock SOAP response
            mock_kursevi = {
                'EUR': Decimal('117.5432'),
                'USD': Decimal('105.2341'),
                'GBP': Decimal('135.6789'),
                'CHF': Decimal('120.3456')
            }
            mock_fetch.return_value = mock_kursevi

            # Call task - should not crash despite Redis failure
            result = update_daily_kursna_lista()

            # Task should still report success (SOAP call succeeded)
            assert result['status'] == 'success'
            assert 'kursevi' in result

    @patch('app.services.nbs_kursna_service.fetch_kursna_lista_soap')
    def test_update_daily_kursna_lista_empty_response(self, mock_fetch, app):
        """Test handling when NBS returns empty kursna lista."""
        with app.app_context():
            # Mock Redis
            redis_mock = Mock()
            app.extensions['redis'] = redis_mock

            # Mock empty SOAP response
            mock_fetch.return_value = {}

            # Call task
            result = update_daily_kursna_lista()

            # Assertions - should be success but with empty kursevi
            assert result['status'] == 'success'
            assert result['kursevi'] == {}

            # Verify no cache writes
            redis_mock.setex.assert_not_called()
