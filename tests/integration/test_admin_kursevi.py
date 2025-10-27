"""Integration tests for Admin Kursevi management."""
import pytest
from unittest.mock import patch, Mock
from decimal import Decimal
from datetime import date
from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma


@pytest.fixture
def admin_user(app):
    """Create an admin user for testing."""
    user = User(
        email='admin@test.com',
        full_name='Test Admin',
        role='admin'
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def pausalac_user(app):
    """Create a pausalac user for testing."""
    firma = PausalnFirma(
        pib='123456789',
        maticni_broj='12345678',
        naziv='Test Firma',
        adresa='Test Address',
        broj='1',
        mesto='Belgrade',
        postanski_broj='11000',
        email='test@firma.com',
        telefon='+381111111111',
        dinarski_racuni=['111-111111-11']
    )
    db.session.add(firma)
    db.session.flush()

    user = User(
        email='pausalac@test.com',
        full_name='Test Pausalac',
        role='pausalac',
        firma_id=firma.id
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user


class TestAdminKursevi:
    """Integration tests for admin kursevi management."""

    @patch('app.routes.admin.get_kurs')
    def test_admin_can_view_kursevi_page(self, mock_get_kurs, client, admin_user):
        """Test admin can view kursevi management page."""
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Mock get_kurs for all currencies
        def mock_kurs(valuta, datum):
            kursevi_map = {
                'EUR': Decimal('117.5432'),
                'USD': Decimal('105.2341'),
                'GBP': Decimal('135.6789'),
                'CHF': Decimal('120.3456')
            }
            return kursevi_map.get(valuta)

        mock_get_kurs.side_effect = mock_kurs

        # Access kursevi page
        response = client.get('/admin/kursevi')

        # Assertions
        assert response.status_code == 200
        assert b'NBS Kursna Lista' in response.data
        assert b'EUR' in response.data
        assert b'USD' in response.data
        assert b'117.5432' in response.data

    @patch('app.routes.admin.cache_kurs')
    @patch('app.routes.admin.get_kurs')
    def test_admin_can_manually_override_kurs(self, mock_get_kurs, mock_cache_kurs, client, admin_user):
        """Test admin can manually override exchange rate."""
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Mock get_kurs (not used in override, but needed for page render)
        mock_get_kurs.return_value = Decimal('117.5432')

        # Submit manual override form
        response = client.post('/admin/kursevi/override', data={
            'csrf_token': 'test',  # WTForms CSRF token (disabled in testing)
            'valuta': 'EUR',
            'kurs': '120.0000',
            'datum': str(date.today())
        }, follow_redirects=True)

        # Assertions
        assert response.status_code == 200
        assert b'Kurs EUR' in response.data
        assert b'120' in response.data

        # Verify cache_kurs was called
        mock_cache_kurs.assert_called_once()
        call_args = mock_cache_kurs.call_args[0]
        assert call_args[0] == 'EUR'
        assert call_args[1] == date.today()
        assert call_args[2] == Decimal('120.0000')

    def test_pausalac_cannot_access_kursevi_page(self, client, pausalac_user):
        """Test pausalac (non-admin) cannot access kursevi page."""
        # Login as pausalac
        client.post('/login', data={
            'email': 'pausalac@test.com',
            'password': 'password123'
        })

        # Try to access kursevi page
        response = client.get('/admin/kursevi')

        # Assertions - should get 403 Forbidden
        assert response.status_code == 403

    @patch('app.routes.admin.cache_kurs')
    @patch('app.routes.admin.get_kurs')
    def test_manual_override_logged_in_security_log(self, mock_get_kurs, mock_cache_kurs, client, admin_user, caplog):
        """Test manual override is logged in security log."""
        import logging

        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Mock get_kurs
        mock_get_kurs.return_value = Decimal('117.5432')

        # Submit manual override form
        with caplog.at_level(logging.INFO, logger='security'):
            response = client.post('/admin/kursevi/override', data={
                'csrf_token': 'test',
                'valuta': 'EUR',
                'kurs': '120.0000',
                'datum': str(date.today())
            }, follow_redirects=True)

        # Assertions
        assert response.status_code == 200

        # Check security log
        security_logs = [record for record in caplog.records if record.name == 'security']
        assert len(security_logs) > 0

        # Check log message contains required info
        override_log = next((log for log in security_logs if 'manually set exchange rate' in log.message), None)
        assert override_log is not None
        assert 'valuta=EUR' in override_log.message
        assert 'kurs=120' in override_log.message
        assert 'admin=admin@test.com' in override_log.message

    @patch('app.routes.admin.get_kurs')
    def test_kursevi_page_shows_unavailable_rates(self, mock_get_kurs, client, admin_user):
        """Test kursevi page shows alert when rates are not available."""
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Mock get_kurs to return None (rate not available)
        mock_get_kurs.return_value = None

        # Access kursevi page
        response = client.get('/admin/kursevi')

        # Assertions
        assert response.status_code == 200
        assert b'Nije dostupan' in response.data
        assert b'Nedostupan' in response.data
        assert b'NBS kursevi nisu dostupni' in response.data

    @patch('app.routes.admin.cache_kurs')
    @patch('app.routes.admin.get_kurs')
    def test_manual_override_validation_rejects_invalid_kurs(self, mock_get_kurs, mock_cache_kurs, client, admin_user):
        """Test form validation rejects invalid kurs values."""
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Mock get_kurs
        mock_get_kurs.return_value = Decimal('117.5432')

        # Submit form with negative kurs
        response = client.post('/admin/kursevi/override', data={
            'csrf_token': 'test',
            'valuta': 'EUR',
            'kurs': '-10.0000',
            'datum': str(date.today())
        }, follow_redirects=True)

        # Assertions - should show validation error
        assert response.status_code == 200

        # Verify cache_kurs was NOT called
        mock_cache_kurs.assert_not_called()

    @patch('app.routes.admin.cache_kurs')
    @patch('app.routes.admin.get_kurs')
    def test_manual_override_with_past_date(self, mock_get_kurs, mock_cache_kurs, client, admin_user):
        """Test admin can set kurs for past dates."""
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Mock get_kurs
        mock_get_kurs.return_value = Decimal('117.5432')

        # Submit form with past date
        past_date = date(2025, 1, 15)
        response = client.post('/admin/kursevi/override', data={
            'csrf_token': 'test',
            'valuta': 'EUR',
            'kurs': '118.0000',
            'datum': str(past_date)
        }, follow_redirects=True)

        # Assertions
        assert response.status_code == 200

        # Verify cache_kurs was called with past date
        mock_cache_kurs.assert_called_once()
        call_args = mock_cache_kurs.call_args[0]
        assert call_args[1] == past_date
