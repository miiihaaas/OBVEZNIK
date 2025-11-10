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


def test_filter_by_firma_admin_god_mode(client, admin_user, test_firma):
    """Test: filter_by_firma() ne filtrira query kada je Admin u god mode-u."""
    from app.utils.query_helpers import filter_by_firma
    from app.models.faktura import Faktura
    from app.models.komitent import Komitent
    from datetime import date

    # Create second firma
    firma2 = PausalnFirma(
        pib='87654321',
        maticni_broj='12345678',
        naziv='Firma 2',
        adresa='Adresa 2',
        broj='2',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        telefon='011234568',
        email='firma2@test.rs',
        dinarski_racuni=[{'banka': 'Banka', 'racun': '123-456789-11'}]
    )
    db.session.add(firma2)
    db.session.commit()

    # Create komitenti for both firme
    komitent1 = Komitent(
        firma_id=test_firma.id,
        pib='11111111',
        naziv='Komitent 1',
        adresa='Adresa 1',
        mesto='Beograd'
    )
    komitent2 = Komitent(
        firma_id=firma2.id,
        pib='22222222',
        naziv='Komitent 2',
        adresa='Adresa 2',
        mesto='Beograd'
    )
    db.session.add_all([komitent1, komitent2])
    db.session.commit()

    # Create fakture for both firme
    faktura1 = Faktura(
        firma_id=test_firma.id,
        komitent_id=komitent1.id,
        user_id=admin_user.id,
        broj_fakture='F1',
        tip_fakture='standardna',
        valuta_fakture='RSD',
        datum_prometa=date.today(),
        valuta_placanja=7,
        datum_dospeca=date.today(),
        ukupan_iznos_rsd=1000.00,
        status='draft'
    )
    faktura2 = Faktura(
        firma_id=firma2.id,
        komitent_id=komitent2.id,
        user_id=admin_user.id,
        broj_fakture='F2',
        tip_fakture='standardna',
        valuta_fakture='RSD',
        datum_prometa=date.today(),
        valuta_placanja=7,
        datum_dospeca=date.today(),
        ukupan_iznos_rsd=2000.00,
        status='draft'
    )
    db.session.add_all([faktura1, faktura2])
    db.session.commit()

    with client:
        # Login as admin (god mode - no firma selected)
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Verify admin is in god mode
        assert get_user_firma_id() is None

        # Query fakture with filter_by_firma
        fakture = filter_by_firma(Faktura.query).all()

        # Admin in god mode sees ALL fakture (no filtering)
        assert len(fakture) == 2
        assert faktura1 in fakture
        assert faktura2 in fakture


def test_filter_by_firma_admin_firm_context(client, admin_user, test_firma):
    """Test: filter_by_firma() filtrira query kada je Admin u firm context-u."""
    from app.utils.query_helpers import filter_by_firma
    from app.models.faktura import Faktura
    from app.models.komitent import Komitent
    from datetime import date

    # Create second firma
    firma2 = PausalnFirma(
        pib='87654321',
        maticni_broj='12345678',
        naziv='Firma 2',
        adresa='Adresa 2',
        broj='2',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        telefon='011234568',
        email='firma2@test.rs',
        dinarski_racuni=[{'banka': 'Banka', 'racun': '123-456789-11'}]
    )
    db.session.add(firma2)
    db.session.commit()

    # Create komitenti for both firme
    komitent1 = Komitent(
        firma_id=test_firma.id,
        pib='11111111',
        naziv='Komitent 1',
        adresa='Adresa 1',
        mesto='Beograd'
    )
    komitent2 = Komitent(
        firma_id=firma2.id,
        pib='22222222',
        naziv='Komitent 2',
        adresa='Adresa 2',
        mesto='Beograd'
    )
    db.session.add_all([komitent1, komitent2])
    db.session.commit()

    # Create fakture for both firme
    faktura1 = Faktura(
        firma_id=test_firma.id,
        komitent_id=komitent1.id,
        user_id=admin_user.id,
        broj_fakture='F1',
        tip_fakture='standardna',
        valuta_fakture='RSD',
        datum_prometa=date.today(),
        valuta_placanja=7,
        datum_dospeca=date.today(),
        ukupan_iznos_rsd=1000.00,
        status='draft'
    )
    faktura2 = Faktura(
        firma_id=firma2.id,
        komitent_id=komitent2.id,
        user_id=admin_user.id,
        broj_fakture='F2',
        tip_fakture='standardna',
        valuta_fakture='RSD',
        datum_prometa=date.today(),
        valuta_placanja=7,
        datum_dospeca=date.today(),
        ukupan_iznos_rsd=2000.00,
        status='draft'
    )
    db.session.add_all([faktura1, faktura2])
    db.session.commit()

    with client:
        # Login as admin and set firm context
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })
        set_admin_firm_context(test_firma.id)

        # Verify admin is in firm context
        assert get_user_firma_id() == test_firma.id

        # Query fakture with filter_by_firma
        fakture = filter_by_firma(Faktura.query).all()

        # Admin in firm context sees ONLY selected firma's fakture
        assert len(fakture) == 1
        assert faktura1 in fakture
        assert faktura2 not in fakture


def test_filter_by_firma_pausalac(client, app, test_firma):
    """Test: filter_by_firma() filtrira query za paušalca."""
    from app.utils.query_helpers import filter_by_firma
    from app.models.faktura import Faktura
    from app.models.komitent import Komitent
    from datetime import date

    # Create second firma
    firma2 = PausalnFirma(
        pib='87654321',
        maticni_broj='12345678',
        naziv='Firma 2',
        adresa='Adresa 2',
        broj='2',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        telefon='011234568',
        email='firma2@test.rs',
        dinarski_racuni=[{'banka': 'Banka', 'racun': '123-456789-11'}]
    )
    db.session.add(firma2)
    db.session.commit()

    # Create pausalac user for test_firma
    pausalac = User(
        email='pausalac3@test.com',
        full_name='Paušalac User 3',
        role='pausalac',
        firma_id=test_firma.id
    )
    pausalac.set_password('password123')
    db.session.add(pausalac)
    db.session.commit()

    # Create komitenti for both firme
    komitent1 = Komitent(
        firma_id=test_firma.id,
        pib='11111111',
        naziv='Komitent 1',
        adresa='Adresa 1',
        mesto='Beograd'
    )
    komitent2 = Komitent(
        firma_id=firma2.id,
        pib='22222222',
        naziv='Komitent 2',
        adresa='Adresa 2',
        mesto='Beograd'
    )
    db.session.add_all([komitent1, komitent2])
    db.session.commit()

    # Create fakture for both firme
    faktura1 = Faktura(
        firma_id=test_firma.id,
        komitent_id=komitent1.id,
        user_id=pausalac.id,
        broj_fakture='F1',
        tip_fakture='standardna',
        valuta_fakture='RSD',
        datum_prometa=date.today(),
        valuta_placanja=7,
        datum_dospeca=date.today(),
        ukupan_iznos_rsd=1000.00,
        status='draft'
    )
    faktura2 = Faktura(
        firma_id=firma2.id,
        komitent_id=komitent2.id,
        user_id=pausalac.id,
        broj_fakture='F2',
        tip_fakture='standardna',
        valuta_fakture='RSD',
        datum_prometa=date.today(),
        valuta_placanja=7,
        datum_dospeca=date.today(),
        ukupan_iznos_rsd=2000.00,
        status='draft'
    )
    db.session.add_all([faktura1, faktura2])
    db.session.commit()

    with client:
        # Login as pausalac
        client.post('/login', data={
            'email': 'pausalac3@test.com',
            'password': 'password123'
        })

        # Verify pausalac firma_id
        assert get_user_firma_id() == test_firma.id

        # Query fakture with filter_by_firma
        fakture = filter_by_firma(Faktura.query).all()

        # Pausalac sees ONLY their firma's fakture
        assert len(fakture) == 1
        assert faktura1 in fakture
        assert faktura2 not in fakture
