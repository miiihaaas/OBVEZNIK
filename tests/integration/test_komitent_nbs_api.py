"""Integration tests for Komitent NBS API endpoint."""
import pytest
from unittest.mock import patch
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app import db


@pytest.fixture
def setup_firma_and_user(app):
    """Create pausalac user with firma for testing."""
    with app.app_context():
        # Create firma
        firma = PausalnFirma(
            pib='12345678',
            maticni_broj='87654321',
            naziv='Test Firma',
            adresa='Test Adresa',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            telefon='011123456',
            email='test@firma.rs',
            dinarski_racuni=[{'banka': 'Intesa', 'broj': '160-123456-78'}]
        )
        db.session.add(firma)
        db.session.commit()

        # Create pausalac user
        pausalac = User(
            email='pausalac@test.com',
            full_name='Pausalac Test',
            role='pausalac',
            firma_id=firma.id
        )
        pausalac.set_password('password123')
        db.session.add(pausalac)
        db.session.commit()

        yield {'firma': firma, 'pausalac': pausalac}


@patch('app.services.nbs_komitent_service.fetch_company_by_pib')
def test_komitent_nbs_api_success(mock_fetch, client, setup_firma_and_user):
    """Test successful NBS API lookup for komitent returns company data."""
    data = setup_firma_and_user

    # Mock NBS service response
    mock_fetch.return_value = {
        'naziv': 'Komitent Test DOO',
        'adresa': 'Bulevar Kralja Aleksandra',
        'broj': '73',
        'mesto': 'Beograd',
        'maticni_broj': '98765432',
        'source': 'nbs'
    }

    with client:
        # Login as pausalac
        response = client.post('/login', data={
            'email': 'pausalac@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # Call NBS API endpoint for komitent
        response = client.get('/komitenti/api/nbs/firma/55555555')
        assert response.status_code == 200

        json_data = response.get_json()
        assert json_data['success'] is True
        assert json_data['data']['naziv'] == 'Komitent Test DOO'
        assert json_data['data']['maticni_broj'] == '98765432'
        assert json_data['data']['adresa'] == 'Bulevar Kralja Aleksandra'
        assert json_data['data']['broj'] == '73'
        assert json_data['data']['mesto'] == 'Beograd'
        assert json_data['data']['source'] == 'nbs'

        # Verify mock was called with correct PIB
        mock_fetch.assert_called_once_with('55555555')


@patch('app.services.nbs_komitent_service.fetch_company_by_pib')
def test_komitent_nbs_api_not_found(mock_fetch, client, setup_firma_and_user):
    """Test NBS API when komitent PIB is not found."""
    data = setup_firma_and_user

    # Mock NBS service to return None (not found)
    mock_fetch.return_value = None

    with client:
        # Login as pausalac
        response = client.post('/login', data={
            'email': 'pausalac@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # Call NBS API endpoint
        response = client.get('/komitenti/api/nbs/firma/99999999')
        assert response.status_code == 200

        json_data = response.get_json()
        assert json_data['success'] is False
        assert 'nije pronađen' in json_data['message'].lower()


def test_komitent_nbs_api_requires_authentication(client):
    """Test that komitent NBS API endpoint requires authentication."""
    # Try to access without login
    response = client.get('/komitenti/api/nbs/firma/12345678', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.location


@patch('app.services.nbs_komitent_service.fetch_company_by_pib')
def test_komitent_create_form_auto_populate_with_nbs(mock_fetch, client, setup_firma_and_user):
    """Test that komitent create form auto-populates with NBS data."""
    data = setup_firma_and_user

    # Mock NBS service response
    mock_fetch.return_value = {
        'naziv': 'Auto-Populated Komitent',
        'adresa': 'Auto Street',
        'broj': '10',
        'mesto': 'Beograd',
        'maticni_broj': '11223344',
        'source': 'nbs'
    }

    with client:
        # Login as pausalac
        response = client.post('/login', data={
            'email': 'pausalac@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # Call NBS API endpoint to get komitent data
        response = client.get('/komitenti/api/nbs/firma/66666666')
        assert response.status_code == 200

        json_data = response.get_json()
        assert json_data['success'] is True

        # Now submit form with NBS-populated data
        response = client.post('/komitenti/novi', data={
            'csrf_token': 'test',
            'pib': '66666666',
            'naziv': json_data['data']['naziv'],
            'maticni_broj': json_data['data']['maticni_broj'],
            'adresa': json_data['data']['adresa'],
            'broj': json_data['data']['broj'],
            'postanski_broj': '11000',
            'mesto': json_data['data']['mesto'],
            'drzava': 'Srbija',
            'email': 'auto@komitent.rs'
        }, follow_redirects=True)

        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        assert 'uspešno kreiran' in response_text or 'Auto-Populated Komitent' in response_text


@patch('app.services.nbs_komitent_service.fetch_company_by_pib')
def test_komitent_nbs_api_handles_service_error_gracefully(mock_fetch, client, setup_firma_and_user):
    """Test that NBS API endpoint handles service errors gracefully."""
    data = setup_firma_and_user

    # Mock NBS service to return None (simulating error/not found)
    mock_fetch.return_value = None

    with client:
        # Login as pausalac
        response = client.post('/login', data={
            'email': 'pausalac@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # Call NBS API endpoint
        response = client.get('/komitenti/api/nbs/firma/12345678')
        assert response.status_code == 200

        json_data = response.get_json()
        assert json_data['success'] is False
        # When NBS service has an error, it returns None, which results in success=False
