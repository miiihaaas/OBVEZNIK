"""Integration tests for Kursevi API endpoint."""
import pytest
from unittest.mock import patch, Mock
from decimal import Decimal
from datetime import date
from app import db
from app.models.user import User


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


class TestKurseviAPI:
    """Integration tests for /api/kursevi endpoint."""

    @patch('app.routes.api.get_kurs')
    def test_get_kursevi_all_currencies(self, mock_get_kurs, client, admin_user):
        """Test GET /api/kursevi returns all currencies for authenticated user."""
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Mock get_kurs to return different rates for each currency
        def mock_kurs(valuta, datum):
            kursevi_map = {
                'EUR': Decimal('117.5432'),
                'USD': Decimal('105.2341'),
                'GBP': Decimal('135.6789'),
                'CHF': Decimal('120.3456')
            }
            return kursevi_map.get(valuta)

        mock_get_kurs.side_effect = mock_kurs

        # Call API endpoint
        response = client.get('/api/kursevi')

        # Assertions
        assert response.status_code == 200
        data = response.get_json()

        assert 'EUR' in data
        assert 'USD' in data
        assert 'GBP' in data
        assert 'CHF' in data
        assert data['EUR'] == '117.5432'
        assert data['USD'] == '105.2341'
        assert data['GBP'] == '135.6789'
        assert data['CHF'] == '120.3456'
        assert 'datum' in data
        assert data['datum'] == str(date.today())

    @patch('app.routes.api.get_kurs')
    def test_get_kursevi_single_currency(self, mock_get_kurs, client, admin_user):
        """Test GET /api/kursevi?valuta=EUR returns single currency."""
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Mock get_kurs
        mock_get_kurs.return_value = Decimal('117.5432')

        # Call API endpoint with valuta parameter
        response = client.get('/api/kursevi?valuta=EUR')

        # Assertions
        assert response.status_code == 200
        data = response.get_json()

        assert 'EUR' in data
        assert data['EUR'] == '117.5432'
        assert 'USD' not in data
        assert 'datum' in data

        # Verify get_kurs was called only for EUR
        mock_get_kurs.assert_called_once()
        call_args = mock_get_kurs.call_args[0]
        assert call_args[0] == 'EUR'

    def test_get_kursevi_unauthenticated(self, client):
        """Test GET /api/kursevi returns 401 for unauthenticated user."""
        # Call API endpoint without authentication
        response = client.get('/api/kursevi')

        # Assertions - should redirect to login (302) or return 401
        assert response.status_code in [302, 401]

    @patch('app.routes.api.get_kurs')
    def test_get_kursevi_nbs_unavailable(self, mock_get_kurs, client, admin_user):
        """Test GET /api/kursevi returns 503 when NBS rates are not available."""
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Mock get_kurs to return None (NBS not available)
        mock_get_kurs.return_value = None

        # Call API endpoint
        response = client.get('/api/kursevi')

        # Assertions
        assert response.status_code == 503
        data = response.get_json()

        assert 'error' in data
        assert 'message' in data
        assert 'missing_currencies' in data
        assert len(data['missing_currencies']) == 4  # All currencies missing

    @patch('app.routes.api.get_kurs')
    def test_get_kursevi_partial_availability(self, mock_get_kurs, client, admin_user):
        """Test GET /api/kursevi returns 503 when some currencies are missing."""
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Mock get_kurs - EUR and USD available, GBP and CHF not
        def mock_kurs(valuta, datum):
            if valuta in ['EUR', 'USD']:
                return Decimal('117.5432')
            else:
                return None  # GBP, CHF not available

        mock_get_kurs.side_effect = mock_kurs

        # Call API endpoint
        response = client.get('/api/kursevi')

        # Assertions
        assert response.status_code == 503
        data = response.get_json()

        assert 'error' in data
        assert 'missing_currencies' in data
        assert 'GBP' in data['missing_currencies']
        assert 'CHF' in data['missing_currencies']

    @patch('app.routes.api.get_kurs')
    def test_get_kursevi_with_date_parameter(self, mock_get_kurs, client, admin_user):
        """Test GET /api/kursevi?datum=2025-01-15 uses specified date."""
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Mock get_kurs
        def mock_kurs(valuta, datum):
            kursevi_map = {
                'EUR': Decimal('117.5432'),
                'USD': Decimal('105.2341'),
                'GBP': Decimal('135.6789'),
                'CHF': Decimal('120.3456')
            }
            return kursevi_map.get(valuta)

        mock_get_kurs.side_effect = mock_kurs

        # Call API endpoint with datum parameter
        response = client.get('/api/kursevi?datum=2025-01-15')

        # Assertions
        assert response.status_code == 200
        data = response.get_json()

        assert data['datum'] == '2025-01-15'

        # Verify get_kurs was called with correct date
        for call in mock_get_kurs.call_args_list:
            assert call[0][1] == date(2025, 1, 15)

    def test_get_kursevi_invalid_date_format(self, client, admin_user):
        """Test GET /api/kursevi?datum=invalid returns 400 error."""
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Call API endpoint with invalid date format
        response = client.get('/api/kursevi?datum=invalid-date')

        # Assertions
        assert response.status_code == 400
        data = response.get_json()

        assert 'error' in data
        assert 'Invalid date format' in data['error']

    def test_get_kursevi_invalid_currency(self, client, admin_user):
        """Test GET /api/kursevi?valuta=XXX returns 400 error."""
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Call API endpoint with invalid currency
        response = client.get('/api/kursevi?valuta=XXX')

        # Assertions
        assert response.status_code == 400
        data = response.get_json()

        assert 'error' in data
        assert 'Invalid currency' in data['error']

    @patch('app.routes.api.get_kurs')
    def test_get_kursevi_case_insensitive_currency(self, mock_get_kurs, client, admin_user):
        """Test GET /api/kursevi?valuta=eur handles lowercase input."""
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Mock get_kurs
        mock_get_kurs.return_value = Decimal('117.5432')

        # Call API endpoint with lowercase valuta
        response = client.get('/api/kursevi?valuta=eur')

        # Assertions
        assert response.status_code == 200
        data = response.get_json()

        assert 'EUR' in data
        assert data['EUR'] == '117.5432'

        # Verify get_kurs was called with uppercase EUR
        call_args = mock_get_kurs.call_args[0]
        assert call_args[0] == 'EUR'
