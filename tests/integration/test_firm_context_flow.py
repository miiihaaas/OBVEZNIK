"""Integration tests for admin firm context switching flow.

Tests the end-to-end flow of admin switching firma context, creating fakture,
and clearing context. Validates navigation changes, session persistence, and
tenant isolation enforcement.
"""
import pytest
from flask import session
from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.komitent import Komitent
from app.models.faktura import Faktura
from datetime import date


@pytest.fixture
def admin_user(app):
    """Create admin user for testing."""
    admin = User(
        email='admin@test.com',
        full_name='Admin User',
        role='admin',
        firma_id=None
    )
    admin.set_password('password123')
    db.session.add(admin)
    db.session.commit()
    return admin


@pytest.fixture
def test_firma(app):
    """Create test firma."""
    firma = PausalnFirma(
        pib='12345678',
        maticni_broj='87654321',
        naziv='Test Firma',
        adresa='Test Adresa',
        broj='1',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        telefon='011234567',
        email='test@test.rs',
        dinarski_racuni=[{'banka': 'Banka', 'racun': '123-456789-10'}]
    )
    db.session.add(firma)
    db.session.commit()
    return firma


@pytest.fixture
def test_komitent(app, test_firma):
    """Create test komitent for test_firma."""
    komitent = Komitent(
        firma_id=test_firma.id,
        pib='11111111',
        maticni_broj='12345678',
        naziv='Test Komitent',
        adresa='Test Adresa',
        broj='1',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        email='test@komitent.rs'
    )
    db.session.add(komitent)
    db.session.commit()
    return komitent


def test_admin_switch_to_firma(client, admin_user, test_firma):
    """Test: Admin može da se prebaci u firm context i vidi paušalac view."""
    # Login as admin
    response = client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200

    # Verify admin is logged in
    with client.session_transaction() as sess:
        assert '_user_id' in sess

    # POST /admin/switch-firma/<firma_id> to switch to firma
    response = client.post(f'/admin/switch-firma/{test_firma.id}', follow_redirects=True)
    assert response.status_code == 200

    # Verify session has admin_selected_firma_id
    with client.session_transaction() as sess:
        assert sess.get('admin_selected_firma_id') == test_firma.id

    # Verify flash message shows firma is selected
    assert 'Selektovana firma'.encode() in response.data or 'Test Firma'.encode() in response.data


def test_admin_clear_firma_context(client, admin_user, test_firma):
    """Test: Admin može da izađe iz firm context-a i vrati se u god mode."""
    # Login as admin
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Switch to firma
    client.post(f'/admin/switch-firma/{test_firma.id}', follow_redirects=True)

    # Verify firma is selected
    with client.session_transaction() as sess:
        assert sess.get('admin_selected_firma_id') == test_firma.id

    # POST /admin/clear-firma-context to exit firm context
    response = client.post('/admin/clear-firma-context', follow_redirects=True)
    assert response.status_code == 200

    # Verify session no longer has admin_selected_firma_id
    with client.session_transaction() as sess:
        assert sess.get('admin_selected_firma_id') is None

    # Verify flash message shows god mode
    assert 'God Mode'.encode() in response.data or 'sve firme'.encode() in response.data


def test_admin_create_faktura_in_firm_context(client, admin_user, test_firma, test_komitent):
    """Test: Admin može da kreira fakturu u firm context-u."""
    # Login as admin and switch to firma
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    client.post(f'/admin/switch-firma/{test_firma.id}', follow_redirects=True)

    # Verify firma is selected
    with client.session_transaction() as sess:
        assert sess.get('admin_selected_firma_id') == test_firma.id

    # POST /fakture/nova to create faktura
    response = client.post('/fakture/nova', data={
        'komitent_id': test_komitent.id,
        'tip_fakture': 'standardna',
        'datum_prometa': date.today().strftime('%Y-%m-%d'),
        'valuta_placanja': 7,
        'stavke-0-naziv': 'Test Artikal',
        'stavke-0-kolicina': 1,
        'stavke-0-jedinica_mere': 'kom',
        'stavke-0-cena': 1000.00
    }, follow_redirects=True)

    # Note: Response might be 200 (success) or redirect, check either way
    assert response.status_code in [200, 302]

    # Verify faktura was created for the selected firma
    faktura = Faktura.query.filter_by(firma_id=test_firma.id).first()
    assert faktura is not None
    assert faktura.firma_id == test_firma.id
    assert faktura.komitent_id == test_komitent.id
    assert faktura.user_id == admin_user.id


def test_admin_cannot_create_faktura_in_god_mode(client, admin_user, test_firma, test_komitent):
    """Test: Admin NE MOŽE da kreira fakturu u god mode-u (bez firm context-a)."""
    # Login as admin (god mode - no firma selected)
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Verify no firma is selected
    with client.session_transaction() as sess:
        assert sess.get('admin_selected_firma_id') is None

    # POST /fakture/nova to attempt creating faktura
    response = client.post('/fakture/nova', data={
        'komitent_id': test_komitent.id,
        'tip_fakture': 'standardna',
        'datum_prometa': date.today().strftime('%Y-%m-%d'),
        'valuta_placanja': 7,
        'stavke-0-naziv': 'Test Artikal',
        'stavke-0-kolicina': 1,
        'stavke-0-jedinica_mere': 'kom',
        'stavke-0-cena': 1000.00
    }, follow_redirects=True)

    # Verify error message is shown
    assert response.status_code == 200
    assert 'Molimo selektujte firmu'.encode() in response.data or 'selektujte firmu'.encode() in response.data

    # Verify faktura was NOT created
    faktura_count = Faktura.query.count()
    assert faktura_count == 0


def test_admin_firm_context_persists_across_requests(client, admin_user, test_firma):
    """Test: Firm context se održava kroz više HTTP requests (session persistence)."""
    # Login as admin and switch to firma
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    client.post(f'/admin/switch-firma/{test_firma.id}', follow_redirects=True)

    # Verify firma is selected
    with client.session_transaction() as sess:
        assert sess.get('admin_selected_firma_id') == test_firma.id

    # Make multiple GET requests to different pages
    # GET /fakture/ (faktlira lista)
    response = client.get('/fakture/')
    assert response.status_code == 200

    # Verify session still has admin_selected_firma_id
    with client.session_transaction() as sess:
        assert sess.get('admin_selected_firma_id') == test_firma.id

    # GET /komitenti/ (komitenti lista)
    response = client.get('/komitenti/')
    assert response.status_code == 200

    # Verify session still has admin_selected_firma_id
    with client.session_transaction() as sess:
        assert sess.get('admin_selected_firma_id') == test_firma.id

    # GET /artikli/ (artikli lista)
    response = client.get('/artikli/')
    assert response.status_code == 200

    # Verify session still has admin_selected_firma_id
    with client.session_transaction() as sess:
        assert sess.get('admin_selected_firma_id') == test_firma.id
