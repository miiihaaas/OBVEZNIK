"""Integration tests for Artikal CRUD operations with tenant isolation."""
import pytest
from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.artikal import Artikal
from decimal import Decimal


@pytest.fixture
def setup_two_firmas_with_artikli(app):
    """Setup two firmas with pausalac users and some artikli."""
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
            dinarski_racuni=[{'racun': '111-111-111', 'banka': 'Banka 1'}],
            drzava='Srbija'
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
            dinarski_racuni=[{'racun': '222-222-222', 'banka': 'Banka 2'}],
            drzava='Srbija'
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

        # Create artikli for firma1
        artikal1 = Artikal(
            firma_id=firma1.id,
            naziv='Programiranje',
            opis='Izrada softvera po satu',
            podrazumevana_cena=Decimal('3500.00'),
            jedinica_mere='sat'
        )
        artikal2 = Artikal(
            firma_id=firma1.id,
            naziv='Konsultacije',
            podrazumevana_cena=Decimal('5000.00'),
            jedinica_mere='sat'
        )
        # Artikal for firma2
        artikal3 = Artikal(
            firma_id=firma2.id,
            naziv='Artikal Firma 2',
            jedinica_mere='kom'
        )
        db.session.add_all([artikal1, artikal2, artikal3])
        db.session.commit()

        yield {
            'firma1': firma1,
            'firma2': firma2,
            'pausalac1': pausalac1,
            'pausalac2': pausalac2,
            'admin': admin,
            'artikal1': artikal1,
            'artikal2': artikal2,
            'artikal3': artikal3
        }


def test_pausalac_can_view_artikli_list(client, setup_two_firmas_with_artikli):
    """Test that pausalac can access artikli list page."""
    # Login as pausalac1
    with client:
        response = client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # Access artikli list
        response = client.get('/artikli/')
        assert response.status_code == 200
        assert b'Artikli i Usluge' in response.data


def test_pausalac_sees_only_own_artikli(client, setup_two_firmas_with_artikli):
    """Test tenant isolation - pausalac only sees their own firma's artikli."""
    data = setup_two_firmas_with_artikli

    # Login as pausalac1
    with client:
        response = client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # Get artikli list
        response = client.get('/artikli/')
        assert response.status_code == 200

        # Should see artikal1 and artikal2 (firma1)
        assert b'Programiranje' in response.data
        assert b'Konsultacije' in response.data
        # Should NOT see artikal3 (firma2)
        assert b'Artikal Firma 2' not in response.data


def test_pausalac_can_create_artikal(client, setup_two_firmas_with_artikli):
    """Test that pausalac can create a new artikal."""
    # Login as pausalac1
    with client:
        client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Create new artikal
        response = client.post('/artikli/novi', data={
            'naziv': 'Dizajn',
            'opis': 'Grafički dizajn',
            'podrazumevana_cena': '2500.00',
            'jedinica_mere': 'sat',
            'csrf_token': client.application.jinja_env.globals['csrf_token']()
        }, follow_redirects=True)

        assert response.status_code == 200
        # Check for success message (use ASCII-safe substring)
        assert b'kreiran' in response.data


def test_pausalac_can_view_artikal_detail(client, setup_two_firmas_with_artikli):
    """Test that pausalac can view artikal detail page."""
    data = setup_two_firmas_with_artikli

    # Login as pausalac1
    with client:
        client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # View artikal detail
        response = client.get(f'/artikli/{data["artikal1"].id}')
        assert response.status_code == 200
        assert b'Programiranje' in response.data
        assert b'Izrada softvera po satu' in response.data


def test_pausalac_can_edit_artikal(client, setup_two_firmas_with_artikli):
    """Test that pausalac can edit their own artikal."""
    data = setup_two_firmas_with_artikli

    # Login as pausalac1
    with client:
        client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Edit artikal
        response = client.post(f'/artikli/{data["artikal1"].id}/izmeni', data={
            'naziv': 'Programiranje Updated',
            'opis': 'Updated opis',
            'podrazumevana_cena': '4000.00',
            'jedinica_mere': 'dan',
            'csrf_token': client.application.jinja_env.globals['csrf_token']()
        }, follow_redirects=True)

        assert response.status_code == 200
        # Check for success message (use ASCII-safe substring)
        assert b'izmenjen' in response.data


def test_pausalac_can_delete_artikal(client, app, setup_two_firmas_with_artikli):
    """Test that pausalac can delete their own artikal."""
    data = setup_two_firmas_with_artikli

    # Login as pausalac1
    with client:
        client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        artikal_id = data["artikal2"].id

        # Delete artikal
        response = client.post(f'/artikli/{artikal_id}/obrisi', data={
            'csrf_token': client.application.jinja_env.globals['csrf_token']()
        }, follow_redirects=True)

        assert response.status_code == 200
        # Check for success message (use ASCII-safe substring)
        assert b'obrisan' in response.data

        # Verify artikal is deleted
        with app.app_context():
            deleted_artikal = db.session.get(Artikal, artikal_id)
            assert deleted_artikal is None


def test_pausalac_cannot_access_other_firma_artikal(client, setup_two_firmas_with_artikli):
    """Test that pausalac cannot access artikal from another firma (403/404)."""
    data = setup_two_firmas_with_artikli

    # Login as pausalac1
    with client:
        client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Try to access artikal3 (belongs to firma2)
        response = client.get(f'/artikli/{data["artikal3"].id}')
        assert response.status_code == 404


def test_pausalac_cannot_edit_other_firma_artikal(client, setup_two_firmas_with_artikli):
    """Test that pausalac cannot edit artikal from another firma."""
    data = setup_two_firmas_with_artikli

    # Login as pausalac1
    with client:
        client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Try to edit artikal3 (belongs to firma2)
        response = client.post(f'/artikli/{data["artikal3"].id}/izmeni', data={
            'naziv': 'Hacked',
            'jedinica_mere': 'kom',
            'csrf_token': client.application.jinja_env.globals['csrf_token']()
        }, follow_redirects=True)

        assert response.status_code == 404


def test_search_functionality(client, setup_two_firmas_with_artikli):
    """Test artikli search functionality."""
    # Login as pausalac1
    with client:
        client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Search for "Programiranje"
        response = client.get('/artikli/?search=Programiranje')
        assert response.status_code == 200
        assert b'Programiranje' in response.data
        # Should NOT see "Konsultacije" (doesn't match search)
        assert b'Konsultacije' not in response.data


def test_sorting_functionality(client, setup_two_firmas_with_artikli):
    """Test artikli sorting functionality."""
    # Login as pausalac1
    with client:
        client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Test sort by naziv ascending
        response = client.get('/artikli/?sort_by=naziv_asc')
        assert response.status_code == 200

        # Test sort by naziv descending
        response = client.get('/artikli/?sort_by=naziv_desc')
        assert response.status_code == 200

        # Test sort by created_at
        response = client.get('/artikli/?sort_by=created_at_desc')
        assert response.status_code == 200


def test_admin_can_view_all_artikli(client, app, setup_two_firmas_with_artikli):
    """Test that admin can view artikli from all firme (god mode)."""
    data = setup_two_firmas_with_artikli

    # Login as admin
    with client:
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        }, follow_redirects=True)

        # Access artikli list (admin sees all)
        response = client.get('/artikli/')
        assert response.status_code == 200

        # Admin can view artikal from firma1
        response = client.get(f'/artikli/{data["artikal1"].id}')
        assert response.status_code == 200

        # Admin can view artikal from firma2
        response = client.get(f'/artikli/{data["artikal3"].id}')
        assert response.status_code == 200
