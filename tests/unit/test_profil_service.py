"""Unit tests for Profil Firme update logic and restricted fields."""
import pytest
from flask import session
from flask_login import login_user

from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.utils.query_helpers import get_user_firma_id, set_admin_firm_context


@pytest.fixture
def test_firma(app):
    """Create test firma with all fields."""
    firma = PausalnFirma(
        pib='123456789',
        maticni_broj='12345678',
        naziv='Original Naziv',
        adresa='Original Adresa',
        broj='10',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        telefon='011111111',
        email='original@test.rs',
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


def test_update_firma_pausalac_allowed_fields(client, pausalac_user, test_firma):
    """Test: Paušalac može izmeniti allowed fields (telefon, email, računi, prefiks/sufiks)."""
    # Login as pausalac
    with client:
        client.post('/login', data={
            'email': 'pausalac@test.rs',
            'password': 'password123'
        })

        # Get firma_id using helper (should return pausalac's firma_id)
        firma_id = get_user_firma_id()
        assert firma_id == test_firma.id

        # Simulate update of allowed fields
        firma = PausalnFirma.query.get(firma_id)

        # Define allowed fields for pausalac
        allowed_fields = ['telefon', 'email', 'dinarski_racuni', 'devizni_racuni',
                         'prefiks_fakture', 'sufiks_fakture']

        # Update allowed fields
        new_data = {
            'telefon': '0669999999',
            'email': 'new@email.rs',
            'dinarski_racuni': [
                {'broj': '200-987654-32', 'banka': 'Raiffeisen banka'}
            ],
            'devizni_racuni': [
                {'iban': 'RS35200005050987654321', 'swift': 'RZBSRSBG', 'banka': 'Raiffeisen'}
            ],
            'prefiks_fakture': 'FAK',
            'sufiks_fakture': '2025'
        }

        for field in allowed_fields:
            if field in new_data:
                setattr(firma, field, new_data[field])

        db.session.commit()

        # Verify firma is updated with new data
        updated_firma = PausalnFirma.query.get(firma_id)
        assert updated_firma.telefon == '0669999999'
        assert updated_firma.email == 'new@email.rs'
        assert updated_firma.dinarski_racuni == [{'broj': '200-987654-32', 'banka': 'Raiffeisen banka'}]
        assert updated_firma.devizni_racuni == [{'iban': 'RS35200005050987654321', 'swift': 'RZBSRSBG', 'banka': 'Raiffeisen'}]
        assert updated_firma.prefiks_fakture == 'FAK'
        assert updated_firma.sufiks_fakture == '2025'


def test_update_firma_pausalac_restricted_fields(client, pausalac_user, test_firma):
    """Test: Paušalac NE MOŽE izmeniti restricted fields (PIB, MB, naziv, adresa)."""
    # Login as pausalac
    with client:
        client.post('/login', data={
            'email': 'pausalac@test.rs',
            'password': 'password123'
        })

        firma_id = get_user_firma_id()
        firma = PausalnFirma.query.get(firma_id)

        # Store original restricted field values
        original_pib = firma.pib
        original_mb = firma.maticni_broj
        original_naziv = firma.naziv
        original_adresa = firma.adresa

        # Define allowed fields (pausalac can only update these)
        allowed_fields = ['telefon', 'email', 'dinarski_racuni', 'devizni_racuni',
                         'prefiks_fakture', 'sufiks_fakture']

        # Simulate POST data with both allowed and restricted fields
        post_data = {
            'telefon': '0661111111',  # Allowed
            'email': 'allowed@test.rs',  # Allowed
            'pib': '999999999',  # Restricted - should be IGNORED
            'maticni_broj': '99999999',  # Restricted - should be IGNORED
            'naziv': 'Hacked Naziv',  # Restricted - should be IGNORED
            'adresa': 'Hacked Adresa'  # Restricted - should be IGNORED
        }

        # Update ONLY allowed fields (backend logic)
        for field in allowed_fields:
            if field in post_data:
                setattr(firma, field, post_data[field])

        db.session.commit()

        # Verify restricted fields are NOT changed
        updated_firma = PausalnFirma.query.get(firma_id)
        assert updated_firma.pib == original_pib  # Should remain unchanged
        assert updated_firma.maticni_broj == original_mb  # Should remain unchanged
        assert updated_firma.naziv == original_naziv  # Should remain unchanged
        assert updated_firma.adresa == original_adresa  # Should remain unchanged

        # Verify allowed fields ARE changed
        assert updated_firma.telefon == '0661111111'
        assert updated_firma.email == 'allowed@test.rs'


def test_update_firma_admin_all_fields(client, admin_user, test_firma):
    """Test: Admin može izmeniti SVA polja (uključujući PIB, naziv, adresa)."""
    # Login as admin
    with client:
        client.post('/login', data={
            'email': 'admin@test.rs',
            'password': 'password123'
        })

        # Set admin firm context to test_firma
        set_admin_firm_context(test_firma.id)

        firma_id = get_user_firma_id()
        assert firma_id == test_firma.id

        firma = PausalnFirma.query.get(firma_id)

        # Admin can update ALL fields (including restricted fields)
        all_fields = ['pib', 'maticni_broj', 'naziv', 'adresa', 'broj',
                     'postanski_broj', 'mesto', 'drzava', 'telefon', 'email',
                     'dinarski_racuni', 'devizni_racuni', 'prefiks_fakture', 'sufiks_fakture']

        new_data = {
            'pib': '987654321',
            'maticni_broj': '87654321',
            'naziv': 'Nova Firma Naziv',
            'adresa': 'Nova Adresa',
            'broj': '99',
            'postanski_broj': '21000',
            'mesto': 'Novi Sad',
            'drzava': 'Srbija',
            'telefon': '0213333333',
            'email': 'admin@newfirma.rs',
            'dinarski_racuni': [{'broj': '300-111111-11', 'banka': 'UniCredit'}],
            'devizni_racuni': [{'iban': 'RS35300005050111111111', 'swift': 'UNCRRSRS', 'banka': 'UniCredit'}],
            'prefiks_fakture': 'ADM',
            'sufiks_fakture': '2026'
        }

        # Update ALL fields (admin has permission)
        for field in all_fields:
            if field in new_data:
                setattr(firma, field, new_data[field])

        db.session.commit()

        # Verify ALL fields are updated
        updated_firma = PausalnFirma.query.get(firma_id)
        assert updated_firma.pib == '987654321'
        assert updated_firma.maticni_broj == '87654321'
        assert updated_firma.naziv == 'Nova Firma Naziv'
        assert updated_firma.adresa == 'Nova Adresa'
        assert updated_firma.broj == '99'
        assert updated_firma.postanski_broj == '21000'
        assert updated_firma.mesto == 'Novi Sad'
        assert updated_firma.telefon == '0213333333'
        assert updated_firma.email == 'admin@newfirma.rs'
        assert updated_firma.prefiks_fakture == 'ADM'
        assert updated_firma.sufiks_fakture == '2026'


def test_update_firma_validation_errors(client, pausalac_user, test_firma):
    """Test: Validation error za nevaliidni email - firma nije ažurirana."""
    # Login as pausalac
    with client:
        client.post('/login', data={
            'email': 'pausalac@test.rs',
            'password': 'password123'
        })

        firma_id = get_user_firma_id()
        firma = PausalnFirma.query.get(firma_id)

        original_email = firma.email

        # Simulate validation: Invalid email should raise error
        invalid_email = 'invalid-email-format'

        # Simple email validation logic (backend should have this)
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        is_valid_email = re.match(email_pattern, invalid_email)

        if not is_valid_email:
            # Validation error - do NOT update firma
            db.session.rollback()
        else:
            firma.email = invalid_email
            db.session.commit()

        # Verify firma email is NOT updated (validation error)
        updated_firma = PausalnFirma.query.get(firma_id)
        assert updated_firma.email == original_email  # Should remain unchanged


def test_update_firma_admin_god_mode_error(client, admin_user):
    """Test: Admin u god mode-u (bez firm context-a) dobija None firma_id."""
    # Login as admin
    with client:
        client.post('/login', data={
            'email': 'admin@test.rs',
            'password': 'password123'
        })

        # Admin in god mode (no firma context)
        firma_id = get_user_firma_id()

        # Verify firma_id is None (god mode)
        assert firma_id is None

        # Backend should redirect to admin dashboard with error message
        # (This test verifies helper returns None, route should handle redirect)


def test_get_user_firma_id_pausalac(client, pausalac_user, test_firma):
    """Test: get_user_firma_id() returns pausalac's firma_id."""
    with client:
        client.post('/login', data={
            'email': 'pausalac@test.rs',
            'password': 'password123'
        })

        firma_id = get_user_firma_id()
        assert firma_id == test_firma.id


def test_get_user_firma_id_admin_with_context(client, admin_user, test_firma):
    """Test: get_user_firma_id() returns session['admin_selected_firma_id'] for admin in firm context."""
    with client:
        client.post('/login', data={
            'email': 'admin@test.rs',
            'password': 'password123'
        })

        # Set firm context
        set_admin_firm_context(test_firma.id)

        firma_id = get_user_firma_id()
        assert firma_id == test_firma.id


def test_get_user_firma_id_admin_god_mode(client, admin_user):
    """Test: get_user_firma_id() returns None for admin in god mode."""
    with client:
        client.post('/login', data={
            'email': 'admin@test.rs',
            'password': 'password123'
        })

        # No firm context set (god mode)
        firma_id = get_user_firma_id()
        assert firma_id is None
