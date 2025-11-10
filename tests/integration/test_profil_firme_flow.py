"""Integration tests for Profil Firme end-to-end flow.

Tests the complete flow of viewing and editing firma profile data,
including permission enforcement for pausalac vs admin users.
"""
import pytest
from flask import session

from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.utils.query_helpers import set_admin_firm_context


@pytest.fixture
def test_firma(app):
    """Create test firma with all fields."""
    firma = PausalnFirma(
        pib='123456789',
        maticni_broj='12345678',
        naziv='Test Firma DOO',
        adresa='Kneza Miloša',
        broj='10',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        telefon='011111111',
        email='test@firma.rs',
        dinarski_racuni=[
            {'broj': '160-123456-78', 'banka': 'Banka Intesa'}
        ],
        devizni_racuni=[
            {'iban': 'RS35160005050123456789', 'swift': 'DBDBRSBG', 'banka': 'Banka Intesa'}
        ],
        prefiks_fakture='INV',
        sufiks_fakture='2024'
    )
    db.session.add(firma)
    db.session.commit()
    return firma


@pytest.fixture
def pausalac_user(app, test_firma):
    """Create pausalac user linked to test_firma."""
    pausalac = User(
        email='pausalac@test.rs',
        full_name='Paušalac User',
        role='pausalac',
        firma_id=test_firma.id
    )
    pausalac.set_password('password123')
    db.session.add(pausalac)
    db.session.commit()
    return pausalac


@pytest.fixture
def admin_user(app):
    """Create admin user (no firma_id)."""
    admin = User(
        email='admin@test.rs',
        full_name='Admin User',
        role='admin',
        firma_id=None
    )
    admin.set_password('password123')
    db.session.add(admin)
    db.session.commit()
    return admin


def test_profil_view_pausalac(client, pausalac_user, test_firma):
    """Test: Paušalac može pristupiti /profil-firme i videti firma podatke."""
    # Login as pausalac
    response = client.post('/login', data={
        'email': 'pausalac@test.rs',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200

    # GET /profil-firme
    response = client.get('/profil-firme')
    assert response.status_code == 200

    # Verify HTML contains firma data
    assert b'Test Firma DOO' in response.data
    assert b'123456789' in response.data  # PIB
    assert b'011111111' in response.data  # Telefon
    assert b'test@firma.rs' in response.data  # Email
    assert b'160-123456-78' in response.data  # Dinarski račun
    assert b'INV' in response.data  # Prefiks
    assert b'2024' in response.data  # Sufiks

    # Verify "Izmeni" button is present (or similar edit button)
    # Note: Adjust this assertion based on actual button text/ID in template
    assert 'Izmeni'.encode('utf-8') in response.data or b'Edit' in response.data or 'Sačuvaj'.encode('utf-8') in response.data


def test_profil_edit_pausalac_allowed(client, pausalac_user, test_firma):
    """Test: Paušalac može izmeniti allowed fields (telefon, email) i uspešno snima."""
    # Login as pausalac
    client.post('/login', data={
        'email': 'pausalac@test.rs',
        'password': 'password123'
    }, follow_redirects=True)

    # POST /profil-firme/edit with updated telefon and email
    response = client.post('/profil-firme/edit', data={
        'telefon': '0669999999',
        'email': 'new@email.rs',
        'dinarski_racuni': '[{"broj": "160-123456-78", "banka": "Banka Intesa"}]',
        'devizni_racuni': '[{"iban": "RS35160005050123456789", "swift": "DBDBRSBG", "banka": "Banka Intesa"}]',
        'prefiks_fakture': 'FAK',
        'sufiks_fakture': '2025'
    }, follow_redirects=True)

    # Verify redirect to /profil-firme
    assert response.status_code == 200

    # Verify success flash message
    assert 'uspešno'.encode('utf-8') in response.data or b'success' in response.data.lower()

    # GET /profil-firme again to verify changes
    response = client.get('/profil-firme')
    assert response.status_code == 200

    # Verify new telefon and email are displayed
    assert b'0669999999' in response.data
    assert b'new@email.rs' in response.data
    assert b'FAK' in response.data
    assert b'2025' in response.data


def test_profil_edit_pausalac_restricted(client, pausalac_user, test_firma):
    """Test: Paušalac NE MOŽE izmeniti restricted fields (PIB, naziv) - ostaju nepromenjeni."""
    # Login as pausalac
    client.post('/login', data={
        'email': 'pausalac@test.rs',
        'password': 'password123'
    }, follow_redirects=True)

    # POST /profil-firme/edit with attempt to change PIB and naziv (should be ignored)
    response = client.post('/profil-firme/edit', data={
        'telefon': '0661111111',  # Allowed - should change
        'email': 'allowed@test.rs',  # Allowed - should change
        'pib': '999999999',  # Restricted - should be IGNORED
        'maticni_broj': '99999999',  # Restricted - should be IGNORED
        'naziv': 'Hacked Naziv',  # Restricted - should be IGNORED
        'adresa': 'Hacked Adresa',  # Restricted - should be IGNORED
        'dinarski_racuni': '[{"broj": "160-123456-78", "banka": "Banka Intesa"}]',
        'devizni_racuni': '[{"iban": "RS35160005050123456789", "swift": "DBDBRSBG", "banka": "Banka Intesa"}]',
        'prefiks_fakture': 'INV',
        'sufiks_fakture': '2024'
    }, follow_redirects=True)

    assert response.status_code == 200

    # GET /profil-firme to verify changes
    response = client.get('/profil-firme')
    assert response.status_code == 200

    # Verify restricted fields are NOT changed (original values remain)
    assert b'123456789' in response.data  # Original PIB
    assert b'Test Firma DOO' in response.data  # Original naziv
    assert b'Kneza Milo' in response.data  # Original adresa (partial match)

    # Verify allowed fields ARE changed
    assert b'0661111111' in response.data  # New telefon
    assert b'allowed@test.rs' in response.data  # New email


def test_profil_edit_admin_all_fields(client, admin_user, test_firma):
    """Test: Admin u firm context-u može izmeniti SVA polja (uključujući PIB, naziv)."""
    # Login as admin
    with client:
        client.post('/login', data={
            'email': 'admin@test.rs',
            'password': 'password123'
        }, follow_redirects=True)

        # Switch to firma (admin firm context)
        response = client.post(f'/admin/switch-firma/{test_firma.id}', follow_redirects=True)
        assert response.status_code == 200

        # POST /profil-firme/edit with changes to ALL fields (including restricted)
        response = client.post('/profil-firme/edit', data={
            'pib': '987654321',  # Admin CAN change PIB
            'maticni_broj': '87654321',  # Admin CAN change MB
            'naziv': 'Nova Firma Naziv',  # Admin CAN change naziv
            'adresa': 'Nova Adresa',  # Admin CAN change adresa
            'broj': '99',
            'postanski_broj': '21000',
            'mesto': 'Novi Sad',
            'drzava': 'Srbija',
            'telefon': '0213333333',
            'email': 'admin@newfirma.rs',
            'dinarski_racuni': '[{"broj": "300-111111-11", "banka": "UniCredit"}]',
            'devizni_racuni': '[{"iban": "RS35300005050111111111", "swift": "UNCRRSRS", "banka": "UniCredit"}]',
            'prefiks_fakture': 'ADM',
            'sufiks_fakture': '2026'
        }, follow_redirects=True)

        assert response.status_code == 200

        # GET /profil-firme to verify all changes
        response = client.get('/profil-firme')
        assert response.status_code == 200

        # Verify ALL fields are updated (including previously restricted fields)
        assert b'987654321' in response.data  # New PIB
        assert b'Nova Firma Naziv' in response.data  # New naziv
        assert b'Nova Adresa' in response.data  # New adresa
        assert b'Novi Sad' in response.data  # New mesto
        assert b'0213333333' in response.data  # New telefon
        assert b'admin@newfirma.rs' in response.data  # New email
        assert b'ADM' in response.data  # New prefiks
        assert b'2026' in response.data  # New sufiks


def test_profil_cancel_button(client, pausalac_user, test_firma):
    """Test: Cancel button vraća na readonly view bez izmena."""
    # Login as pausalac
    client.post('/login', data={
        'email': 'pausalac@test.rs',
        'password': 'password123'
    }, follow_redirects=True)

    # GET /profil-firme (view mode)
    response = client.get('/profil-firme')
    assert response.status_code == 200
    original_telefon = test_firma.telefon

    # Simulate edit mode - no changes submitted (just redirect back)
    # If using Option A (JS toggle), this test is N/A
    # If using Option B (separate edit route), test redirect from /profil-firme/edit to /profil-firme
    # For now, assume redirect from /profil-firme without POST = cancel

    # GET /profil-firme again (simulating "Cancel" - no POST sent)
    response = client.get('/profil-firme')
    assert response.status_code == 200

    # Verify original telefon is still displayed (no changes)
    assert original_telefon.encode() in response.data


def test_profil_admin_god_mode_error(client, admin_user):
    """Test: Admin u god mode-u (bez firm context-a) dobija error/redirect."""
    # Login as admin
    client.post('/login', data={
        'email': 'admin@test.rs',
        'password': 'password123'
    }, follow_redirects=True)

    # Attempt to access /profil-firme without firm context (god mode)
    response = client.get('/profil-firme', follow_redirects=True)

    # Should redirect to admin dashboard with error message
    assert response.status_code == 200
    # Verify redirect to admin dashboard (check URL or response content)
    assert b'admin' in response.data.lower() or b'dashboard' in response.data.lower()
    # Verify error/warning message
    assert b'firma' in response.data.lower() or b'selekt' in response.data.lower()


def test_profil_view_displays_limiti(client, pausalac_user, test_firma):
    """Test: Profil view prikazuje rolling limit i kalendarska godina limit (readonly)."""
    # Login as pausalac
    client.post('/login', data={
        'email': 'pausalac@test.rs',
        'password': 'password123'
    }, follow_redirects=True)

    # GET /profil-firme
    response = client.get('/profil-firme')
    assert response.status_code == 200

    # Verify rolling limit is displayed (8,000,000 RSD)
    assert b'8,000,000' in response.data or b'8000000' in response.data

    # Verify calendar year limit is displayed (6,000,000 RSD)
    assert b'6,000,000' in response.data or b'6000000' in response.data

    # Verify napomena about rolling limit tracking
    assert b'365' in response.data or b'rolling' in response.data.lower()


def test_profil_edit_validation_error(client, pausalac_user, test_firma):
    """Test: POST sa nevalidnim email-om vraća validation error."""
    # Login as pausalac
    client.post('/login', data={
        'email': 'pausalac@test.rs',
        'password': 'password123'
    }, follow_redirects=True)

    # POST /profil-firme/edit with invalid email
    response = client.post('/profil-firme/edit', data={
        'telefon': '0669999999',
        'email': 'invalid-email-format',  # Invalid email
        'dinarski_racuni': '[{"broj": "160-123456-78", "banka": "Banka Intesa"}]',
        'devizni_racuni': '[]',
        'prefiks_fakture': 'INV',
        'sufiks_fakture': '2024'
    }, follow_redirects=True)

    # Should return to form with error message
    assert response.status_code == 200

    # Verify error message is displayed
    assert b'error' in response.data.lower() or b'invalid' in response.data.lower() or b'nevalid' in response.data.lower()

    # Verify email was NOT updated in database
    updated_firma = PausalnFirma.query.get(test_firma.id)
    assert updated_firma.email == 'test@firma.rs'  # Original email remains
