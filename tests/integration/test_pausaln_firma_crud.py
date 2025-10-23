"""Integration tests for PausalnFirma CRUD operations."""
import pytest
import json
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


def test_admin_can_access_firme_list(client, admin_user):
    """Test that admin can access paušalne firme list."""
    # Login as admin
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    })

    # Access firme list
    response = client.get('/admin/firme')
    assert response.status_code == 200
    assert 'Paušalne Firme' in response.data.decode('utf-8')


def test_admin_can_access_firma_create_form(client, admin_user):
    """Test that admin can access firma creation form."""
    # Login as admin
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    })

    # Access firma create form
    response = client.get('/admin/firme/nova')
    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    assert 'Dodaj' in response_text
    assert 'PIB' in response_text


def test_admin_can_create_firma_with_valid_data(client, admin_user, app):
    """Test that admin can create new paušalna firma with valid data."""
    # Login as admin
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    })

    # Create firma
    response = client.post('/admin/firme/nova', data={
        'pib': '12345678',
        'naziv': 'Test Firma DOO',
        'maticni_broj': '87654321',
        'adresa': 'Kneza Miloša',
        'broj': '12',
        'postanski_broj': '11000',
        'mesto': 'Beograd',
        'drzava': 'Srbija',
        'telefon': '+381 11 1234567',
        'email': 'info@testfirma.rs',
        'dinarski_racuni_json': json.dumps([{'banka': 'Intesa', 'broj': '160-123456-78'}]),
        'devizni_racuni_json': json.dumps([]),
        'prefiks_fakture': 'TEST',
        'sufiks_fakture': '/2025',
        'pdv_kategorija': 'SS',
        'sifra_osnova': 'PDV-RS-33',
        'csrf_token': 'dummy'  # CSRF disabled in testing
    }, follow_redirects=True)

    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    assert 'uspešno kreirana' in response_text or 'Test Firma DOO' in response_text

    # Verify firma was created in database
    with app.app_context():
        firma = PausalnFirma.query.filter_by(pib='12345678').first()
        assert firma is not None
        assert firma.naziv == 'Test Firma DOO'
        assert firma.maticni_broj == '87654321'
        assert firma.mesto == 'Beograd'


def test_admin_cannot_create_firma_with_duplicate_pib(client, admin_user, app):
    """Test that admin cannot create firma with duplicate PIB."""
    # Login as admin
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    })

    # Create first firma
    with app.app_context():
        firma = PausalnFirma(
            pib='12345678',
            maticni_broj='87654321',
            naziv='Existing Firma',
            adresa='Test',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            telefon='011123456',
            email='test@test.rs',
            dinarski_racuni=[{'banka': 'test', 'broj': '123'}]
        )
        db.session.add(firma)
        db.session.commit()

    # Try to create firma with duplicate PIB
    response = client.post('/admin/firme/nova', data={
        'pib': '12345678',  # Duplicate
        'naziv': 'New Firma',
        'maticni_broj': '11111111',
        'adresa': 'Test',
        'broj': '1',
        'postanski_broj': '11000',
        'mesto': 'Beograd',
        'drzava': 'Srbija',
        'telefon': '011123456',
        'email': 'new@test.rs',
        'dinarski_racuni_json': json.dumps([{'banka': 'test', 'broj': '123'}]),
        'csrf_token': 'dummy'
    }, follow_redirects=True)

    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    assert 'već postoji' in response_text or 'Greška' in response_text


def test_admin_can_view_firma_details(client, admin_user, app):
    """Test that admin can view firma details."""
    # Create firma
    with app.app_context():
        firma = PausalnFirma(
            pib='12345678',
            maticni_broj='87654321',
            naziv='Detail Test Firma',
            adresa='Test',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            telefon='011123456',
            email='detail@test.rs',
            dinarski_racuni=[{'banka': 'Intesa', 'broj': '160-123456-78'}]
        )
        db.session.add(firma)
        db.session.commit()
        firma_id = firma.id

    # Login as admin
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    })

    # View firma details
    response = client.get(f'/admin/firme/{firma_id}')
    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    assert 'Detail Test Firma' in response_text
    assert '12345678' in response_text
    assert 'Beograd' in response_text


def test_pausalac_cannot_access_admin_firma_routes(client, app):
    """Test that paušalac cannot access admin firma routes."""
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

    # Login as pausalac
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'pausalac123'
    })

    # Try to access admin firma routes
    response = client.get('/admin/firme')
    assert response.status_code == 403  # Forbidden

    response = client.get('/admin/firme/nova')
    assert response.status_code == 403  # Forbidden


def test_unauthenticated_user_cannot_access_firma_routes(client):
    """Test that unauthenticated user is redirected to login."""
    response = client.get('/admin/firme', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.location

    response = client.get('/admin/firme/nova', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.location


def test_firma_create_validates_required_fields(client, admin_user):
    """Test that firma creation validates required fields."""
    # Login as admin
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    })

    # Try to create firma with missing required fields
    response = client.post('/admin/firme/nova', data={
        'pib': '12345678',
        # Missing naziv
        'maticni_broj': '87654321',
        'adresa': 'Test',
        'broj': '1',
        'postanski_broj': '11000',
        'mesto': 'Beograd',
        'drzava': 'Srbija',
        'telefon': '011123456',
        'dinarski_racuni_json': json.dumps([{'banka': 'test', 'broj': '123'}]),
        'csrf_token': 'dummy'
    }, follow_redirects=True)

    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    # Should show validation error
    assert 'obavezan' in response_text or 'required' in response_text.lower()


def test_firma_creation_logs_security_event(client, admin_user, app, caplog):
    """Test that firma creation logs security event."""
    import logging

    # Login as admin
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    })

    # Create firma with logging capture
    with caplog.at_level(logging.INFO, logger='security'):
        client.post('/admin/firme/nova', data={
            'pib': '12345678',
            'naziv': 'Security Log Test',
            'maticni_broj': '87654321',
            'adresa': 'Test',
            'broj': '1',
            'postanski_broj': '11000',
            'mesto': 'Beograd',
            'drzava': 'Srbija',
            'telefon': '011123456',
            'email': 'security@test.rs',
            'dinarski_racuni_json': json.dumps([{'banka': 'test', 'broj': '123'}]),
            'csrf_token': 'dummy'
        }, follow_redirects=True)

    # Assert: Security log entry exists
    assert 'PausalnFirma created' in caplog.text
    assert 'admin@test.com' in caplog.text
    assert '12345678' in caplog.text
