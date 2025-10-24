"""Integration tests for NBS Komitent API endpoint."""
import pytest
from unittest.mock import patch
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app import create_app, db


@pytest.fixture
def app():
    """Create test app with test config."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def admin_user(app):
    """Create admin user for testing."""
    with app.app_context():
        user = User(email='admin@test.com', full_name='Admin Test', role='admin')
        user.set_password('admin123')
        db.session.add(user)
        db.session.commit()
        return user


@patch('app.services.nbs_komitent_service.fetch_company_by_pib')
def test_nbs_api_success(mock_fetch, client, admin_user):
    """Test successful NBS API lookup returns company data."""
    # Mock NBS service response
    mock_fetch.return_value = {
        'naziv': 'Test Firma DOO',
        'adresa': 'Kneza Miloša',
        'broj': '12',
        'mesto': 'Beograd',
        'maticni_broj': '87654321',
        'source': 'nbs'
    }

    # Login as admin
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    })

    # Call NBS API endpoint
    response = client.get('/api/nbs/firma/12345678')
    assert response.status_code == 200

    json_data = response.get_json()
    assert json_data['success'] is True
    assert json_data['data']['naziv'] == 'Test Firma DOO'
    assert json_data['data']['maticni_broj'] == '87654321'
    assert json_data['data']['source'] == 'nbs'

    # Verify mock was called with correct PIB
    mock_fetch.assert_called_once_with('12345678')


@patch('app.services.nbs_komitent_service.fetch_company_by_pib')
def test_nbs_api_not_found(mock_fetch, client, admin_user):
    """Test NBS API when PIB is not found."""
    # Mock NBS service to return None (not found)
    mock_fetch.return_value = None

    # Login as admin
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    })

    # Call NBS API endpoint
    response = client.get('/api/nbs/firma/99999999')
    assert response.status_code == 200

    json_data = response.get_json()
    assert json_data['success'] is False
    assert 'nije pronađena' in json_data['message']


@patch('app.services.nbs_komitent_service.fetch_company_by_pib')
def test_nbs_api_invalid_pib_format(mock_fetch, client, admin_user):
    """Test NBS API with invalid PIB format returns 400 error."""
    # Mock to return None (not found) for valid format tests
    mock_fetch.return_value = None

    # Login as admin
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    })

    # Test short PIB (should return 400 - invalid format)
    response = client.get('/api/nbs/firma/123')
    assert response.status_code == 400
    json_data = response.get_json()
    assert 'error' in json_data
    assert 'Invalid PIB format' in json_data['error']

    # Test too long PIB (should return 400 - invalid format)
    response = client.get('/api/nbs/firma/12345678901')
    assert response.status_code == 400

    # Test non-numeric PIB (should return 400 - invalid format)
    response = client.get('/api/nbs/firma/1234567a')
    assert response.status_code == 400

    # Test 8 digits (should return 200 - valid format, even if not found)
    response = client.get('/api/nbs/firma/12345678')
    assert response.status_code == 200

    # Test 9 digits (should return 200 - valid format, even if not found)
    response = client.get('/api/nbs/firma/123456789')
    assert response.status_code == 200


def test_nbs_api_requires_authentication(client):
    """Test that NBS API endpoint requires authentication."""
    # Try to access without login
    response = client.get('/api/nbs/firma/12345678', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.location


@patch('app.services.nbs_komitent_service.fetch_company_by_pib')
def test_nbs_api_accessible_by_pausalac(mock_fetch, client, app):
    """Test that paušalac users can also access NBS API (not admin-only)."""
    # Create paušalac user
    with app.app_context():
        firma = PausalnFirma(
            pib='99999999',
            maticni_broj='88888888',
            naziv='Pausalac Firma',
            adresa='Test',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            telefon='011123456',
            email='pau@test.rs',
            dinarski_racuni=[{'banka': 'test', 'broj': '123'}]
        )
        db.session.add(firma)
        db.session.flush()

        user = User(email='pausalac@test.com', full_name='Pausalac Test', role='pausalac', firma_id=firma.id)
        user.set_password('pausalac123')
        db.session.add(user)
        db.session.commit()

    # Mock NBS service response
    mock_fetch.return_value = {
        'naziv': 'Test',
        'adresa': 'Test',
        'broj': '1',
        'mesto': 'Beograd',
        'maticni_broj': '12345678',
        'source': 'nbs'
    }

    # Login as pausalac
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'pausalac123'
    })

    # Call NBS API endpoint
    response = client.get('/api/nbs/firma/12345678')
    assert response.status_code == 200

    json_data = response.get_json()
    assert json_data['success'] is True
