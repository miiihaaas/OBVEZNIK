"""Integration tests for admin god mode functionality.

Tests the complete admin god mode flow including firm switching,
context persistence, and access to komitenti/artikli data.
"""
import pytest
from flask import session
from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.komitent import Komitent
from app.models.artikal import Artikal


@pytest.fixture
def admin_user(app):
    """Create admin user for testing."""
    admin = User(
        email='admin_godmode@test.com',
        full_name='Admin God Mode',
        role='admin',
        firma_id=None
    )
    admin.set_password('password123')
    db.session.add(admin)
    db.session.commit()
    return admin


@pytest.fixture
def pausalac_user(app, firma1):
    """Create pausalac user for testing."""
    pausalac = User(
        email='pausalac_godmode@test.com',
        full_name='Paušalac User',
        role='pausalac',
        firma_id=firma1.id
    )
    pausalac.set_password('password123')
    db.session.add(pausalac)
    db.session.commit()
    return pausalac


@pytest.fixture
def firma1(app):
    """Create first test firma."""
    firma = PausalnFirma(
        pib='11111111',
        maticni_broj='11111111',
        naziv='Firma A',
        adresa='Adresa A',
        broj='1',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        telefon='011111111',
        email='firma_a@test.rs',
        dinarski_racuni=[{'banka': 'Banka A', 'racun': '111-111111-11'}]
    )
    db.session.add(firma)
    db.session.commit()
    return firma


@pytest.fixture
def firma2(app):
    """Create second test firma."""
    firma = PausalnFirma(
        pib='22222222',
        maticni_broj='22222222',
        naziv='Firma B',
        adresa='Adresa B',
        broj='2',
        postanski_broj='21000',
        mesto='Novi Sad',
        drzava='Srbija',
        telefon='022222222',
        email='firma_b@test.rs',
        dinarski_racuni=[{'banka': 'Banka B', 'racun': '222-222222-22'}]
    )
    db.session.add(firma)
    db.session.commit()
    return firma


@pytest.fixture
def komitenti_firma1(app, firma1):
    """Create komitenti for firma1."""
    komitent1 = Komitent(
        pib='33333333',
        maticni_broj='33333333',
        naziv='Komitent A1',
        adresa='Adresa A1',
        broj='1',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        email='komitent_a1@test.rs',
        firma_id=firma1.id
    )
    komitent2 = Komitent(
        pib='44444444',
        maticni_broj='44444444',
        naziv='Komitent A2',
        adresa='Adresa A2',
        broj='2',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        email='komitent_a2@test.rs',
        firma_id=firma1.id
    )
    db.session.add(komitent1)
    db.session.add(komitent2)
    db.session.commit()
    return [komitent1, komitent2]


@pytest.fixture
def komitenti_firma2(app, firma2):
    """Create komitenti for firma2."""
    komitent1 = Komitent(
        pib='55555555',
        maticni_broj='55555555',
        naziv='Komitent B1',
        adresa='Adresa B1',
        broj='1',
        postanski_broj='21000',
        mesto='Novi Sad',
        drzava='Srbija',
        email='komitent_b1@test.rs',
        firma_id=firma2.id
    )
    db.session.add(komitent1)
    db.session.commit()
    return [komitent1]


@pytest.fixture
def artikli_firma1(app, firma1):
    """Create artikli for firma1."""
    artikal1 = Artikal(
        naziv='Artikal A1',
        sifra='A001',
        jedinica_mere='kom',
        cena=100.00,
        firma_id=firma1.id
    )
    artikal2 = Artikal(
        naziv='Artikal A2',
        sifra='A002',
        jedinica_mere='kg',
        cena=200.00,
        firma_id=firma1.id
    )
    db.session.add(artikal1)
    db.session.add(artikal2)
    db.session.commit()
    return [artikal1, artikal2]


@pytest.fixture
def artikli_firma2(app, firma2):
    """Create artikli for firma2."""
    artikal1 = Artikal(
        naziv='Artikal B1',
        sifra='B001',
        jedinica_mere='kom',
        cena=150.00,
        firma_id=firma2.id
    )
    db.session.add(artikal1)
    db.session.commit()
    return [artikal1]


def test_admin_without_firm_context_sees_all_komitenti(
    client, admin_user, firma1, firma2, komitenti_firma1, komitenti_firma2
):
    """Test: Admin bez firm context-a vidi sve komitente svih firmi."""
    with client:
        # Logout any previous user
        client.get('/logout', follow_redirects=True)

        # Login as admin
        client.post('/login', data={
            'email': 'admin_godmode@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Access komitenti list (no firm context set)
        response = client.get('/komitenti', follow_redirects=True)

        # Verify response
        assert response.status_code == 200

        # Admin should see komitenti from both firme (total 3)
        assert b'Komitent A1' in response.data
        assert b'Komitent A2' in response.data
        assert b'Komitent B1' in response.data


def test_admin_with_firm_context_sees_only_that_firma_komitenti(
    client, admin_user, firma1, firma2, komitenti_firma1, komitenti_firma2
):
    """Test: Admin sa firm context-om vidi samo komitente te firme."""
    with client:
        # Logout any previous user
        client.get('/logout', follow_redirects=True)

        # Login as admin
        client.post('/login', data={
            'email': 'admin_godmode@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Switch to firma1
        client.post(f'/admin/switch-firma/{firma1.id}', follow_redirects=True)

        # Access komitenti list
        response = client.get('/komitenti', follow_redirects=True)

        # Verify response
        assert response.status_code == 200

        # Admin should see only firma1 komitenti
        assert b'Komitent A1' in response.data
        assert b'Komitent A2' in response.data
        assert b'Komitent B1' not in response.data


def test_admin_can_switch_firma(client, admin_user, firma1, firma2):
    """Test: Admin može switch-ovati firmu (POST `/admin/switch-firma/<id>`)."""
    with client:
        # Logout any previous user
        client.get('/logout', follow_redirects=True)

        # Login as admin
        client.post('/login', data={
            'email': 'admin_godmode@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Switch to firma1
        response = client.post(
            f'/admin/switch-firma/{firma1.id}',
            follow_redirects=True
        )

        # Verify response
        assert response.status_code == 200
        assert session['admin_selected_firma_id'] == firma1.id
        assert b'Firma A' in response.data

        # Switch to firma2
        response = client.post(
            f'/admin/switch-firma/{firma2.id}',
            follow_redirects=True
        )

        # Verify response
        assert response.status_code == 200
        assert session['admin_selected_firma_id'] == firma2.id
        assert b'Firma B' in response.data


def test_admin_can_clear_firma_context(client, admin_user, firma1):
    """Test: Admin može clear-ovati firm context (POST `/admin/clear-firma-context`)."""
    with client:
        # Logout any previous user
        client.get('/logout', follow_redirects=True)

        # Login as admin
        client.post('/login', data={
            'email': 'admin_godmode@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Switch to firma1
        client.post(f'/admin/switch-firma/{firma1.id}', follow_redirects=True)
        assert session['admin_selected_firma_id'] == firma1.id

        # Clear firm context
        response = client.post('/admin/clear-firma-context', follow_redirects=True)

        # Verify response
        assert response.status_code == 200
        assert 'admin_selected_firma_id' not in session
        assert b'God Mode' in response.data


def test_pausalac_cannot_access_admin_routes(client, pausalac_user, firma1):
    """Test: Paušalac ne može pristupiti admin routes (403 Forbidden)."""
    with client:
        # Logout any previous user
        client.get('/logout', follow_redirects=True)

        # Login as pausalac
        client.post('/login', data={
            'email': 'pausalac_godmode@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Try to switch firma (should fail with 403)
        response = client.post(f'/admin/switch-firma/{firma1.id}')
        assert response.status_code == 403

        # Try to clear firm context (should fail with 403)
        response = client.post('/admin/clear-firma-context')
        assert response.status_code == 403


def test_admin_firm_context_persists_across_requests(client, admin_user, firma1):
    """Test: Admin firm context persists across multiple requests (session-based)."""
    with client:
        # Logout any previous user
        client.get('/logout', follow_redirects=True)

        # Login as admin
        client.post('/login', data={
            'email': 'admin_godmode@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Switch to firma1
        client.post(f'/admin/switch-firma/{firma1.id}', follow_redirects=True)
        assert session['admin_selected_firma_id'] == firma1.id

        # Make multiple requests and verify context persists
        client.get('/komitenti', follow_redirects=True)
        assert session['admin_selected_firma_id'] == firma1.id

        client.get('/artikli', follow_redirects=True)
        assert session['admin_selected_firma_id'] == firma1.id

        client.get('/admin/firme', follow_redirects=True)
        assert session['admin_selected_firma_id'] == firma1.id
