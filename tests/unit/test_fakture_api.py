"""Unit tests for Fakture API endpoints."""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.komitent import Komitent
from app.models.faktura import Faktura
from app.services.dashboard_service import ROLLING_LIMIT_365_DAYS


@pytest.fixture
def test_data(app):
    """Create test data: firms, users, komitenti, and invoices."""
    with app.app_context():
        # Create test firma
        firma = PausalnFirma(
            pib='111111111',
            maticni_broj='11111111',
            naziv='Test Firma',
            adresa='Test Adresa',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            telefon='011111111',
            email='test@test.com',
            dinarski_racuni=[{'banka': 'Test Banka', 'racun': '111-111111-11'}]
        )
        db.session.add(firma)
        db.session.commit()

        # Create users
        admin_user = User(
            email='admin@test.com',
            full_name='Admin User',
            role='admin'
        )
        admin_user.set_password('password123')

        pausalac_user = User(
            email='pausalac@test.com',
            full_name='Pausalac User',
            role='pausalac',
            firma_id=firma.id
        )
        pausalac_user.set_password('password123')

        db.session.add_all([admin_user, pausalac_user])
        db.session.commit()

        # Create komitent
        komitent = Komitent(
            firma_id=firma.id,
            pib='444444444',
            maticni_broj='44444444',
            naziv='Test Komitent',
            adresa='Komitent Adresa',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            email='komitent@test.com'
        )
        db.session.add(komitent)
        db.session.commit()

        # Create test invoices within 365 days (promet_365_dana = 5,000,000 RSD)
        today = date.today()
        for i in range(5):
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=pausalac_user.id,
                broj_fakture=f'TEST-{i+1}/2025',
                datum_prometa=today - timedelta(days=i*30),  # Spread across 150 days
                datum_dospeca=today - timedelta(days=i*30) + timedelta(days=30),
                valuta_placanja=30,
                tip_fakture='standardna',
                valuta_fakture='RSD',
                status='izdata',
                ukupan_iznos_rsd=Decimal('1000000.00')  # 1M per invoice = 5M total
            )
            db.session.add(faktura)

        db.session.commit()

        # Return IDs instead of objects to avoid DetachedInstanceError
        return {
            'firma_id': firma.id,
            'admin_user_id': admin_user.id,
            'pausalac_user_id': pausalac_user.id,
            'komitent_id': komitent.id
        }


def test_get_limit_widget_data_pausalac(client, test_data):
    """Test API endpoint for pausalac user (AC: 6)."""
    # Login as pausalac
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    })

    # GET API endpoint
    response = client.get('/fakture/api/limit-widget-data')

    # Assertions
    assert response.status_code == 200

    data = response.get_json()
    assert 'rolling_limit' in data
    assert data['rolling_limit'] == ROLLING_LIMIT_365_DAYS
    assert 'promet_365_dana' in data
    assert data['promet_365_dana'] == 5000000  # 5 invoices * 1M
    assert 'preostali_limit' in data
    assert data['preostali_limit'] == 3000000  # 8M - 5M
    assert 'progress_percentage' in data
    assert 'progress_color' in data
    assert data['progress_color'] == 'success'  # < 70%
    assert 'projekcija_7' in data
    assert 'projekcija_15' in data
    assert 'projekcija_30' in data
    # No simulation
    assert data['nova_faktura_iznos'] == 0
    assert data['preostalo_nakon_nove'] == 3000000
    assert data['over_limit'] is False
    assert data['over_limit_amount'] == 0


def test_get_limit_widget_data_with_nova_faktura(client, test_data):
    """Test API endpoint with nova_faktura_iznos parameter (simulation) (AC: 6)."""
    # Login as pausalac
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    })

    # GET API endpoint with nova_faktura_iznos parameter
    response = client.get('/fakture/api/limit-widget-data?nova_faktura_iznos=500000')

    # Assertions
    assert response.status_code == 200

    data = response.get_json()
    assert data['nova_faktura_iznos'] == 500000
    assert data['preostalo_nakon_nove'] == 2500000  # 3M - 0.5M
    assert data['over_limit'] is False
    assert data['over_limit_amount'] == 0


def test_get_limit_widget_data_over_limit(client, app):
    """Test API endpoint with over limit scenario (AC: 6)."""
    with app.app_context():
        # Create test firma with high promet (7,800,000 RSD)
        firma = PausalnFirma(
            pib='222222222',
            maticni_broj='22222222',
            naziv='High Promet Firma',
            adresa='Adresa 2',
            broj='2',
            postanski_broj='21000',
            mesto='Novi Sad',
            telefon='021222222',
            email='high@test.com',
            dinarski_racuni=[{'banka': 'Test Banka', 'racun': '222-222222-22'}]
        )
        db.session.add(firma)
        db.session.commit()

        pausalac = User(
            email='highpausalac@test.com',
            full_name='High Pausalac',
            role='pausalac',
            firma_id=firma.id
        )
        pausalac.set_password('password123')
        db.session.add(pausalac)
        db.session.commit()

        komitent = Komitent(
            firma_id=firma.id,
            pib='555555555',
            maticni_broj='55555555',
            naziv='High Komitent',
            adresa='Adresa 5',
            broj='5',
            postanski_broj='21000',
            mesto='Novi Sad',
            drzava='Srbija',
            email='high@komitent.com'
        )
        db.session.add(komitent)
        db.session.commit()

        # Create invoices totaling 7,800,000 RSD
        today = date.today()
        for i in range(39):  # 39 invoices * 200,000 = 7,800,000
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=pausalac.id,
                broj_fakture=f'HIGH-{i+1}/2025',
                datum_prometa=today - timedelta(days=i*9),  # Spread across 351 days
                datum_dospeca=today - timedelta(days=i*9) + timedelta(days=30),
                valuta_placanja=30,
                tip_fakture='standardna',
                valuta_fakture='RSD',
                status='izdata',
                ukupan_iznos_rsd=Decimal('200000.00')
            )
            db.session.add(faktura)

        db.session.commit()

    # Login as pausalac
    client.post('/login', data={
        'email': 'highpausalac@test.com',
        'password': 'password123'
    })

    # GET API endpoint with nova_faktura_iznos that exceeds limit
    response = client.get('/fakture/api/limit-widget-data?nova_faktura_iznos=500000')

    # Assertions
    assert response.status_code == 200

    data = response.get_json()
    assert data['promet_365_dana'] == 7800000  # 39 * 200k
    assert data['preostali_limit'] == 200000  # 8M - 7.8M
    assert data['nova_faktura_iznos'] == 500000
    assert data['preostalo_nakon_nove'] == -300000  # 200k - 500k
    assert data['over_limit'] is True
    assert data['over_limit_amount'] == 300000


def test_get_limit_widget_data_admin_firm_context(client, test_data):
    """Test API endpoint for admin in firm context (AC: 6)."""
    # Login as admin
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'password123'
    })

    # Switch to firma context
    with client.session_transaction() as session:
        session['admin_selected_firma_id'] = test_data['firma_id']

    # GET API endpoint
    response = client.get('/fakture/api/limit-widget-data')

    # Assertions
    assert response.status_code == 200

    data = response.get_json()
    assert data['rolling_limit'] == ROLLING_LIMIT_365_DAYS
    assert data['promet_365_dana'] == 5000000  # Same as pausalac test
    assert data['preostali_limit'] == 3000000


def test_get_limit_widget_data_admin_god_mode_error(client, test_data):
    """Test API endpoint returns error for admin in god mode (no firm context) (AC: 6)."""
    # Login as admin (god mode - no firm context)
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'password123'
    })

    # GET API endpoint (admin in god mode)
    response = client.get('/fakture/api/limit-widget-data')

    # Assertions
    assert response.status_code == 400

    data = response.get_json()
    assert 'error' in data
    assert 'selektujte firmu' in data['error'].lower()
