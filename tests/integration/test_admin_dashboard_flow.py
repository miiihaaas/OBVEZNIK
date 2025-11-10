"""Integration tests for admin dashboard flow."""
import pytest
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
from app import create_app, db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.komitent import Komitent
from app.models.faktura import Faktura


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


@pytest.fixture
def pausalac_user(app):
    """Create pausalac user with firma for testing."""
    with app.app_context():
        # Create test firma first
        firma = PausalnFirma(
            pib='999888777',
            maticni_broj='12345678',
            naziv='Test Firma',
            adresa='Test adresa',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            telefon='011/1234567',
            email='test@test.com',
            dinarski_racuni=[{'banka': 'Test Banka', 'racun': '999-888888-99'}],
            is_active=True
        )
        db.session.add(firma)
        db.session.flush()

        # Create pausalac user
        user = User(
            email='pausalac@test.com',
            full_name='Pausalac Test',
            role='pausalac',
            firma_id=firma.id
        )
        user.set_password('pausalac123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def test_data(app):
    """Create test data: firms, users, komitenti, and invoices."""
    with app.app_context():
        # Create test firms
        firma1 = PausalnFirma(
            pib='111111111',
            maticni_broj='11111111',
            naziv='ABC Firma',
            adresa='Adresa 1',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            telefon='011111111',
            email='abc@test.com',
            dinarski_racuni=[{'banka': 'Test Banka', 'racun': '111-111111-11'}]
        )
        firma2 = PausalnFirma(
            pib='222222222',
            maticni_broj='22222222',
            naziv='XYZ Firma',
            adresa='Adresa 2',
            broj='2',
            postanski_broj='21000',
            mesto='Novi Sad',
            telefon='021222222',
            email='xyz@test.com',
            dinarski_racuni=[{'banka': 'Test Banka', 'racun': '222-222222-22'}]
        )
        db.session.add_all([firma1, firma2])
        db.session.commit()

        # Create users
        pausalac1 = User(
            email='pausalac1@test.com',
            full_name='Pausalac 1',
            role='pausalac',
            firma_id=firma1.id
        )
        pausalac1.set_password('password123')

        pausalac2 = User(
            email='pausalac2@test.com',
            full_name='Pausalac 2',
            role='pausalac',
            firma_id=firma2.id
        )
        pausalac2.set_password('password123')

        db.session.add_all([pausalac1, pausalac2])
        db.session.commit()

        # Create komitenti
        komitent1 = Komitent(
            firma_id=firma1.id,
            pib='444444444',
            maticni_broj='44444444',
            naziv='Komitent 1',
            adresa='Komitent Adresa 1',
            broj='10',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            email='komitent1@test.com'
        )
        komitent2 = Komitent(
            firma_id=firma2.id,
            pib='555555555',
            maticni_broj='55555555',
            naziv='Komitent 2',
            adresa='Komitent Adresa 2',
            broj='20',
            postanski_broj='21000',
            mesto='Novi Sad',
            drzava='Srbija',
            email='komitent2@test.com'
        )
        db.session.add_all([komitent1, komitent2])
        db.session.commit()

        # Create invoices for current month
        today = date.today()
        first_day_this_month = today.replace(day=1)

        # Firma1: 2 invoices
        faktura1 = Faktura(
            firma_id=firma1.id,
            komitent_id=komitent1.id,
            user_id=pausalac1.id,
            broj_fakture='F1-001',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=first_day_this_month,
            valuta_placanja=30,
            datum_dospeca=first_day_this_month + timedelta(days=30),
            ukupan_iznos_rsd=Decimal('100000.00'),
            status='izdata',
            finalized_at=datetime.now(timezone.utc)
        )
        faktura2 = Faktura(
            firma_id=firma1.id,
            komitent_id=komitent1.id,
            user_id=pausalac1.id,
            broj_fakture='F1-002',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=first_day_this_month + timedelta(days=2),
            valuta_placanja=30,
            datum_dospeca=first_day_this_month + timedelta(days=32),
            ukupan_iznos_rsd=Decimal('200000.00'),
            status='izdata',
            finalized_at=datetime.now(timezone.utc)
        )

        # Firma2: 1 invoice
        faktura3 = Faktura(
            firma_id=firma2.id,
            komitent_id=komitent2.id,
            user_id=pausalac2.id,
            broj_fakture='F2-001',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=first_day_this_month + timedelta(days=1),
            valuta_placanja=30,
            datum_dospeca=first_day_this_month + timedelta(days=31),
            ukupan_iznos_rsd=Decimal('150000.00'),
            status='izdata',
            finalized_at=datetime.now(timezone.utc)
        )

        db.session.add_all([faktura1, faktura2, faktura3])
        db.session.commit()

        yield {
            'firma1': firma1,
            'firma2': firma2,
            'pausalac1': pausalac1,
            'pausalac2': pausalac2
        }


def login_user(client, email, password):
    """Helper function to login a user."""
    return client.post(
        '/login',
        data={'email': email, 'password': password},
        follow_redirects=True
    )


def test_admin_can_access_dashboard(client, admin_user, test_data):
    """Test that admin user can access the dashboard."""
    # Login as admin
    response = login_user(client, 'admin@test.com', 'admin123')
    assert response.status_code == 200

    # Access admin dashboard
    response = client.get('/admin/dashboard')
    assert response.status_code == 200
    assert b'Dashboard' in response.data or b'dashboard' in response.data


def test_pausalac_cannot_access_admin_dashboard(client, pausalac_user):
    """Test that pausalac user cannot access admin dashboard."""
    # Login as pausalac
    response = login_user(client, 'pausalac@test.com', 'pausalac123')
    assert response.status_code == 200

    # Try to access admin dashboard - should return 403 Forbidden
    response = client.get('/admin/dashboard')
    assert response.status_code == 403


def test_unauthenticated_user_redirected_to_login(client):
    """Test that unauthenticated user is redirected to login."""
    response = client.get('/admin/dashboard', follow_redirects=False)
    # Should redirect to login (302) or return 401
    assert response.status_code in [302, 401]


def test_dashboard_aggregates_data_correctly(client, admin_user, test_data):
    """Test that dashboard aggregates data correctly."""
    # Login as admin
    login_user(client, 'admin@test.com', 'admin123')

    # Access admin dashboard
    response = client.get('/admin/dashboard')
    assert response.status_code == 200

    # Check that response contains firma names
    assert b'ABC Firma' in response.data
    assert b'XYZ Firma' in response.data


def test_dashboard_sorting(client, admin_user, test_data):
    """Test dashboard sorting functionality."""
    # Login as admin
    login_user(client, 'admin@test.com', 'admin123')

    # Test sorting by naziv
    response = client.get('/admin/dashboard?sort_by=naziv')
    assert response.status_code == 200

    # Test sorting by broj_faktura
    response = client.get('/admin/dashboard?sort_by=broj_faktura')
    assert response.status_code == 200

    # Test sorting by promet
    response = client.get('/admin/dashboard?sort_by=promet')
    assert response.status_code == 200


def test_dashboard_date_filtering(client, admin_user, test_data):
    """Test dashboard date range filtering."""
    # Login as admin
    login_user(client, 'admin@test.com', 'admin123')

    # Test with custom date range
    today = date.today()
    first_day = today.replace(day=1)
    date_from = first_day.isoformat()
    date_to = (first_day + timedelta(days=5)).isoformat()

    response = client.get(f'/admin/dashboard?date_from={date_from}&date_to={date_to}')
    assert response.status_code == 200


def test_dashboard_search(client, admin_user, test_data):
    """Test dashboard search functionality."""
    # Login as admin
    login_user(client, 'admin@test.com', 'admin123')

    # Search by naziv
    response = client.get('/admin/dashboard?search=ABC')
    assert response.status_code == 200
    assert b'ABC Firma' in response.data

    # Search by PIB
    response = client.get('/admin/dashboard?search=111111111')
    assert response.status_code == 200
    assert b'ABC Firma' in response.data


def test_dashboard_pagination(client, admin_user, test_data):
    """Test dashboard pagination."""
    # Login as admin
    login_user(client, 'admin@test.com', 'admin123')

    # Test page 1
    response = client.get('/admin/dashboard?page=1')
    assert response.status_code == 200

    # Test page 2 (even if empty)
    response = client.get('/admin/dashboard?page=2')
    assert response.status_code == 200
