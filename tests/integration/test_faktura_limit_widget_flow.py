"""
Integration tests for Faktura Limit Widget Flow (Story 5.4).

Tests the complete limit tracking widget functionality on nova faktura form,
including initial load, simulation, over limit warnings, and admin firm context.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.komitent import Komitent
from app.models.faktura import Faktura
from app.services.dashboard_service import ROLLING_LIMIT_365_DAYS


@pytest.fixture
def pausalac_with_fakture(app):
    """Create pausalac user with firma and test fakture (promet = 5,000,000 RSD)."""
    with app.app_context():
        # Create firma
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
        db.session.flush()

        # Create pausalac user
        pausalac = User(
            email='pausalac@test.com',
            full_name='Pausalac User',
            role='pausalac',
            firma_id=firma.id
        )
        pausalac.set_password('password123')
        db.session.add(pausalac)
        db.session.flush()

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
        db.session.flush()

        # Create test invoices (promet_365_dana = 5,000,000 RSD)
        today = date.today()
        for i in range(5):
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=pausalac.id,
                broj_fakture=f'TEST-{i+1}/2025',
                datum_prometa=today - timedelta(days=i*30),
                datum_dospeca=today - timedelta(days=i*30) + timedelta(days=30),
                valuta_placanja=30,
                tip_fakture='standardna',
                valuta_fakture='RSD',
                status='izdata',
                ukupan_iznos_rsd=Decimal('1000000.00')
            )
            db.session.add(faktura)

        db.session.commit()

        return {
            'firma_id': firma.id,
            'pausalac_id': pausalac.id,
            'komitent_id': komitent.id
        }


@pytest.fixture
def pausalac_high_promet(app):
    """Create pausalac user with high promet (7,800,000 RSD) for over limit testing."""
    with app.app_context():
        # Create firma
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
        db.session.flush()

        pausalac = User(
            email='highpausalac@test.com',
            full_name='High Pausalac',
            role='pausalac',
            firma_id=firma.id
        )
        pausalac.set_password('password123')
        db.session.add(pausalac)
        db.session.flush()

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
        db.session.flush()

        # Create invoices totaling 7,800,000 RSD
        today = date.today()
        for i in range(39):  # 39 * 200,000 = 7,800,000
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=pausalac.id,
                broj_fakture=f'HIGH-{i+1}/2025',
                datum_prometa=today - timedelta(days=i*9),
                datum_dospeca=today - timedelta(days=i*9) + timedelta(days=30),
                valuta_placanja=30,
                tip_fakture='standardna',
                valuta_fakture='RSD',
                status='izdata',
                ukupan_iznos_rsd=Decimal('200000.00')
            )
            db.session.add(faktura)

        db.session.commit()

        return {
            'firma_id': firma.id,
            'pausalac_id': pausalac.id,
            'komitent_id': komitent.id
        }


@pytest.fixture
def admin_user(app):
    """Create admin user for admin firm context testing."""
    with app.app_context():
        admin = User(
            email='admin@test.com',
            full_name='Admin User',
            role='admin'
        )
        admin.set_password('password123')
        db.session.add(admin)
        db.session.commit()

        return {
            'admin_id': admin.id
        }


def test_limit_widget_initial_load(client, pausalac_with_fakture):
    """Test initial load of limit widget on nova faktura form (AC: 2, 3, 4, 5)."""
    # Login as pausalac
    response = client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200

    # GET nova faktura form
    response = client.get('/fakture/nova')
    assert response.status_code == 200

    # Verify limit widget HTML is present
    html = response.data.decode('utf-8')
    assert 'id="limit_widget"' in html
    assert 'Limit Tracking' in html
    assert 'id="limit_loading"' in html
    assert 'id="limit_content"' in html

    # GET API endpoint to verify data
    response = client.get('/fakture/api/limit-widget-data')
    assert response.status_code == 200

    data = response.get_json()
    assert data['rolling_limit'] == ROLLING_LIMIT_365_DAYS
    assert data['promet_365_dana'] == 5000000
    assert data['preostali_limit'] == 3000000
    assert data['nova_faktura_iznos'] == 0
    assert data['preostalo_nakon_nove'] == 3000000
    assert data['over_limit'] is False


def test_limit_widget_nova_faktura_simulation(client, pausalac_with_fakture):
    """Test limit widget simulation with nova_faktura_iznos parameter (AC: 2, 4)."""
    # Login as pausalac
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # GET API endpoint with nova_faktura_iznos
    response = client.get('/fakture/api/limit-widget-data?nova_faktura_iznos=500000')
    assert response.status_code == 200

    data = response.get_json()
    assert data['nova_faktura_iznos'] == 500000
    assert data['preostalo_nakon_nove'] == 2500000  # 3M - 0.5M
    assert data['over_limit'] is False
    assert data['over_limit_amount'] == 0


def test_limit_widget_over_limit_warning(client, pausalac_high_promet):
    """Test limit widget over limit warning scenario (AC: 3)."""
    # Login as pausalac with high promet
    client.post('/login', data={
        'email': 'highpausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # GET API endpoint with nova_faktura_iznos that exceeds limit
    response = client.get('/fakture/api/limit-widget-data?nova_faktura_iznos=500000')
    assert response.status_code == 200

    data = response.get_json()
    assert data['promet_365_dana'] == 7800000
    assert data['preostali_limit'] == 200000  # 8M - 7.8M
    assert data['nova_faktura_iznos'] == 500000
    assert data['preostalo_nakon_nove'] == -300000  # 200k - 500k
    assert data['over_limit'] is True
    assert data['over_limit_amount'] == 300000


def test_limit_widget_admin_firm_context(client, pausalac_with_fakture, admin_user):
    """Test limit widget for admin in firm context (AC: 5)."""
    # Login as admin
    response = client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200

    # Switch to firma context
    with client.session_transaction() as session:
        session['admin_selected_firma_id'] = pausalac_with_fakture['firma_id']

    # GET nova faktura form
    response = client.get('/fakture/nova')
    assert response.status_code == 200

    # Verify limit widget is present
    html = response.data.decode('utf-8')
    assert 'id="limit_widget"' in html

    # GET API endpoint
    response = client.get('/fakture/api/limit-widget-data')
    assert response.status_code == 200

    data = response.get_json()
    assert data['rolling_limit'] == ROLLING_LIMIT_365_DAYS
    assert data['promet_365_dana'] == 5000000  # Same as pausalac
    assert data['preostali_limit'] == 3000000
