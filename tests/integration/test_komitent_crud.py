"""Integration tests for Komitent CRUD operations with tenant isolation."""
import pytest
from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.komitent import Komitent
from flask_login import login_user


@pytest.fixture
def setup_two_firmas_with_users(app):
    """Setup two firmas with pausalac users and some komitenti."""
    with app.app_context():
        # Create two pausaln firmas
        firma1 = PausalnFirma(
            pib='111111111',
            naziv='Firma 1',
            adresa='Adresa 1',
            broj='1',
            mesto='Beograd',
            postanski_broj='11000',
            maticni_broj='11111111',
            telefon='011111111',
            email='firma1@test.rs',
            dinarski_racuni=[{'racun': '111-111-111', 'banka': 'Banka 1'}]
        )
        firma2 = PausalnFirma(
            pib='222222222',
            naziv='Firma 2',
            adresa='Adresa 2',
            broj='2',
            mesto='Novi Sad',
            postanski_broj='21000',
            maticni_broj='22222222',
            telefon='021222222',
            email='firma2@test.rs',
            dinarski_racuni=[{'racun': '222-222-222', 'banka': 'Banka 2'}]
        )
        db.session.add_all([firma1, firma2])
        db.session.commit()

        # Create pausalac users
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

        # Create admin user
        admin = User(
            email='admin@test.com',
            full_name='Admin User',
            role='admin',
            firma_id=None
        )
        admin.set_password('admin123')

        db.session.add_all([pausalac1, pausalac2, admin])
        db.session.commit()

        # Create komitenti for firma1
        komitent1 = Komitent(
            firma_id=firma1.id,
            pib='333333333',
            maticni_broj='33333333',
            naziv='Komitent Firma 1',
            adresa='Komitent Adresa 1',
            broj='10',
            mesto='Beograd',
            postanski_broj='11000',
            drzava='Srbija',
            email='komitent1@test.rs'
        )
        komitent2 = Komitent(
            firma_id=firma2.id,
            pib='444444444',
            maticni_broj='44444444',
            naziv='Komitent Firma 2',
            adresa='Komitent Adresa 2',
            broj='20',
            mesto='Novi Sad',
            postanski_broj='21000',
            drzava='Srbija',
            email='komitent2@test.rs'
        )
        db.session.add_all([komitent1, komitent2])
        db.session.commit()

        yield {
            'firma1': firma1,
            'firma2': firma2,
            'pausalac1': pausalac1,
            'pausalac2': pausalac2,
            'admin': admin,
            'komitent1': komitent1,
            'komitent2': komitent2
        }


def test_pausalac_can_view_komitenti_list(client, setup_two_firmas_with_users):
    """Test that pausalac can access komitenti list page."""
    data = setup_two_firmas_with_users

    # Login as pausalac1
    with client:
        response = client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # Access komitenti list
        response = client.get('/komitenti/')
        assert response.status_code == 200
        assert b'Komitenti' in response.data


def test_pausalac_sees_only_own_komitenti(client, app, setup_two_firmas_with_users):
    """Test tenant isolation - pausalac only sees their own firma's komitenti."""
    data = setup_two_firmas_with_users

    # Login as pausalac1
    with client:
        response = client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # Get komitenti list
        response = client.get('/komitenti/')
        assert response.status_code == 200

        # Should see komitent1 (firma1)
        assert b'Komitent Firma 1' in response.data
        # Should NOT see komitent2 (firma2)
        assert b'Komitent Firma 2' not in response.data


def test_pausalac_can_create_komitent(client, setup_two_firmas_with_users):
    """Test that pausalac can create a new komitent."""
    data = setup_two_firmas_with_users

    with client:
        # Login as pausalac1
        response = client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # Create new komitent
        response = client.post('/komitenti/novi', data={
            'csrf_token': 'test',  # CSRF will be handled by test config
            'pib': '55555555',
            'naziv': 'Novi Komitent',
            'maticni_broj': '55555555',
            'adresa': 'Nova Ulica',
            'broj': '5',
            'postanski_broj': '11000',
            'mesto': 'Beograd',
            'drzava': 'Srbija',
            'email': 'novi@komitent.rs'
        }, follow_redirects=True)

        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        assert 'uspešno kreiran' in response_text or 'Novi Komitent' in response_text


def test_pausalac_can_view_komitent_detail(client, setup_two_firmas_with_users):
    """Test that pausalac can view komitent detail page."""
    data = setup_two_firmas_with_users

    with client:
        # Login as pausalac1
        response = client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # View komitent detail
        komitent_id = data['komitent1'].id
        response = client.get(f'/komitenti/{komitent_id}')
        assert response.status_code == 200
        assert b'Komitent Firma 1' in response.data
        assert b'333333333' in response.data  # PIB


def test_pausalac_cannot_view_other_firma_komitent(client, setup_two_firmas_with_users):
    """Test that pausalac cannot view komitent from another firma (404)."""
    data = setup_two_firmas_with_users

    with client:
        # Login as pausalac1
        response = client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # Try to view komitent2 (belongs to firma2)
        komitent_id = data['komitent2'].id
        response = client.get(f'/komitenti/{komitent_id}')
        assert response.status_code == 404


def test_pausalac_can_edit_komitent(client, setup_two_firmas_with_users):
    """Test that pausalac can edit their own komitent."""
    data = setup_two_firmas_with_users

    with client:
        # Login as pausalac1
        response = client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # Edit komitent
        komitent_id = data['komitent1'].id
        response = client.post(f'/komitenti/{komitent_id}/izmeni', data={
            'csrf_token': 'test',
            'pib': '333333333',  # PIB remains the same (readonly)
            'naziv': 'Updated Komitent Naziv',
            'maticni_broj': '33333333',
            'adresa': 'Updated Adresa',
            'broj': '11',
            'postanski_broj': '11000',
            'mesto': 'Beograd',
            'drzava': 'Srbija',
            'email': 'updated@komitent.rs'
        }, follow_redirects=True)

        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        assert 'uspešno izmenjen' in response_text or 'Updated Komitent Naziv' in response_text


def test_pausalac_cannot_edit_other_firma_komitent(client, setup_two_firmas_with_users):
    """Test that pausalac cannot edit komitent from another firma (404)."""
    data = setup_two_firmas_with_users

    with client:
        # Login as pausalac1
        response = client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # Try to edit komitent2 (belongs to firma2)
        komitent_id = data['komitent2'].id
        response = client.post(f'/komitenti/{komitent_id}/izmeni', data={
            'csrf_token': 'test',
            'pib': '444444444',
            'naziv': 'Hacked Naziv',
            'maticni_broj': '44444444',
            'adresa': 'Hacked',
            'broj': '1',
            'postanski_broj': '21000',
            'mesto': 'Novi Sad',
            'drzava': 'Srbija',
            'email': 'hacked@test.rs'
        }, follow_redirects=True)

        assert response.status_code == 404


def test_pausalac_can_delete_komitent_without_fakture(client, setup_two_firmas_with_users):
    """Test that pausalac can delete komitent without fakture."""
    data = setup_two_firmas_with_users

    with client:
        # Login as pausalac1
        response = client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # Delete komitent (no fakture)
        komitent_id = data['komitent1'].id
        response = client.post(f'/komitenti/{komitent_id}/obrisi', data={
            'csrf_token': 'test'
        }, follow_redirects=True)

        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        assert 'uspešno obrisan' in response_text


def test_pausalac_cannot_delete_komitent_with_fakture(client, app, setup_two_firmas_with_users):
    """Test that pausalac CANNOT delete komitent with fakture (RESTRICT constraint)."""
    data = setup_two_firmas_with_users

    with app.app_context():
        # Import Faktura model
        from app.models.faktura import Faktura
        from datetime import datetime, timezone, timedelta

        # Create faktura for komitent1
        faktura = Faktura(
            firma_id=data['firma1'].id,
            user_id=data['pausalac1'].id,
            komitent_id=data['komitent1'].id,
            broj_fakture='F-001',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=datetime.now(timezone.utc).date(),
            valuta_placanja=15,
            datum_dospeca=datetime.now(timezone.utc).date() + timedelta(days=15),
            status='izdata',
            ukupan_iznos_rsd=1000.00
        )
        db.session.add(faktura)
        db.session.commit()

    with client:
        # Login as pausalac1
        response = client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # Try to delete komitent (has fakture)
        komitent_id = data['komitent1'].id
        response = client.post(f'/komitenti/{komitent_id}/obrisi', data={
            'csrf_token': 'test'
        }, follow_redirects=True)

        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        assert 'fakture' in response_text or 'Ne možete obrisati' in response_text


def test_search_filter_komitenti(client, setup_two_firmas_with_users):
    """Test search/filter functionality for komitenti."""
    data = setup_two_firmas_with_users

    with client:
        # Login as pausalac1
        response = client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # Search by naziv
        response = client.get('/komitenti/?search=Komitent Firma 1')
        assert response.status_code == 200
        assert b'Komitent Firma 1' in response.data

        # Search by PIB
        response = client.get('/komitenti/?search=333333333')
        assert response.status_code == 200
        assert b'Komitent Firma 1' in response.data


def test_admin_can_view_all_komitenti(client, app, setup_two_firmas_with_users):
    """Test that admin can view komitenti from all firme (god mode)."""
    data = setup_two_firmas_with_users

    # Login as admin
    with client:
        response = client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # Test with query helpers
        with app.test_request_context():
            from flask_login import login_user
            from app.utils.query_helpers import filter_by_firma

            admin = User.query.filter_by(email='admin@test.com').first()
            login_user(admin)

            # Admin should see komitenti from all firme
            komitenti = filter_by_firma(Komitent.query).all()
            assert len(komitenti) >= 2  # At least komitent1 and komitent2
