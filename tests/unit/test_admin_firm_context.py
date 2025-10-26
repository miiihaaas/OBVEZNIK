"""Unit tests for admin firm context functionality.

Tests the session-based firma selection system that allows admin users
to optionally view and manage data for a specific firma only.
"""
import pytest
from flask import session
from app import db
from app.utils.query_helpers import (
    get_admin_selected_firma_id,
    get_user_firma_id,
    set_admin_firm_context,
    clear_admin_firm_context
)
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma


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
def pausalac_user(app, test_firma):
    """Create pausalac user for testing."""
    pausalac = User(
        email='pausalac@test.com',
        full_name='Paušalac User',
        role='pausalac',
        firma_id=test_firma.id
    )
    pausalac.set_password('password123')
    db.session.add(pausalac)
    db.session.commit()
    return pausalac


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


def test_admin_without_selected_firma_has_god_mode(client, admin_user):
    """Test: Admin bez selektovane firme vidi sve podatke (god mode)."""
    with client:
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Verify no firma is selected (god mode)
        assert get_admin_selected_firma_id() is None
        assert get_user_firma_id() is None  # None = god mode (no filtering)


def test_admin_with_selected_firma_sees_only_that_firma(client, admin_user, test_firma):
    """Test: Admin sa selektovanom firmom vidi samo podatke te firme."""
    with client:
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Set admin firm context to test_firma
        set_admin_firm_context(test_firma.id)

        # Verify firma is selected
        assert get_admin_selected_firma_id() == test_firma.id
        assert get_user_firma_id() == test_firma.id  # Admin now filtered by firma


def test_pausalac_cannot_use_admin_firm_context(client, app, test_firma):
    """Test: Paušalac ne može koristiti admin firm context (ignored)."""
    from flask_login import current_user

    # Create pausalac user directly in test
    pausalac = User(
        email='pausalac2@test.com',
        full_name='Paušalac User 2',
        role='pausalac',
        firma_id=test_firma.id
    )
    pausalac.set_password('password123')
    db.session.add(pausalac)
    db.session.commit()

    with client:
        # Logout any previous user first
        client.get('/logout', follow_redirects=True)

        # Login as pausalac
        response = client.post('/login', data={
            'email': 'pausalac2@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Verify login succeeded
        assert response.status_code == 200
        assert current_user.is_authenticated
        assert current_user.role == 'pausalac'
        assert current_user.firma_id == test_firma.id

        # Try to set admin firm context (should be ignored)
        set_admin_firm_context(999)  # Different firma_id

        # Verify pausalac still sees only their own firma
        assert get_admin_selected_firma_id() == 999  # Session value set
        assert get_user_firma_id() == test_firma.id  # But pausalac uses their firma_id


def test_set_admin_firm_context_sets_session(client, admin_user, test_firma):
    """Test: set_admin_firm_context() postavlja session['admin_selected_firma_id']."""
    with client:
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Set admin firm context
        set_admin_firm_context(test_firma.id)

        # Verify session value is set
        assert session.get('admin_selected_firma_id') == test_firma.id
        assert get_admin_selected_firma_id() == test_firma.id


def test_clear_admin_firm_context_clears_session(client, admin_user, test_firma):
    """Test: clear_admin_firm_context() čisti session['admin_selected_firma_id']."""
    with client:
        # Logout any previous user first
        client.get('/logout', follow_redirects=True)

        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Set admin firm context
        set_admin_firm_context(test_firma.id)
        assert session.get('admin_selected_firma_id') == test_firma.id

        # Clear admin firm context
        clear_admin_firm_context()

        # Verify session value is cleared
        assert session.get('admin_selected_firma_id') is None
        assert get_admin_selected_firma_id() is None
        assert get_user_firma_id() is None  # Admin back to god mode
