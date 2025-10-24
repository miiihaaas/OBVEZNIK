"""Integration tests for PausalnFirma Edit and Delete flows."""
import pytest
from app.models.pausaln_firma import PausalnFirma
from app.models.user import User
from app import db
import json


class TestPausalnFirmaEditFlow:
    """Test complete edit flow for PausalnFirma."""

    def test_admin_can_access_edit_form(self, client, admin_user, sample_firma):
        """Test that admin can access edit form with prepopulated data."""
        with client:
            # Login as admin
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'admin123'
            })

            # GET edit form
            response = client.get(f'/admin/firme/{sample_firma.id}/izmeni')
            assert response.status_code == 200
            assert b'Izmeni' in response.data
            assert sample_firma.naziv.encode() in response.data
            assert sample_firma.pib.encode() in response.data
            assert b'readonly' in response.data  # PIB should be readonly

    def test_admin_can_edit_firma_and_see_success_message(self, app, client, admin_user, sample_firma):
        """Test that admin can successfully edit firma and see success message."""
        with client:
            # Login as admin
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'admin123'
            })

            # POST update (CSRF is disabled in testing config)
            response = client.post(f'/admin/firme/{sample_firma.id}/izmeni', data={
                'pib': sample_firma.pib,
                'naziv': 'Updated Firma DOO',
                'maticni_broj': '87654321',
                'adresa': 'Updated Ulica',
                'broj': '99',
                'postanski_broj': '11000',
                'mesto': 'Beograd',
                'drzava': 'Srbija',
                'telefon': '011999888',
                'email': 'updated@firma.rs',
                'dinarski_racuni_json': json.dumps([{'banka': 'Updated Banka', 'broj': '999-999999-99'}]),
                'devizni_racuni_json': json.dumps([]),
                'prefiks_fakture': 'UPD',
                'sufiks_fakture': '2025',
                'pdv_kategorija': 'SS',
                'sifra_osnova': 'PDV-RS-33'
            }, follow_redirects=True)

            assert response.status_code == 200
            assert 'uspešno izmenjena' in response.data.decode('utf-8')

            # Verify changes in database
            with app.app_context():
                updated_firma = db.session.get(PausalnFirma, sample_firma.id)
                assert updated_firma.naziv == 'Updated Firma DOO'
                assert updated_firma.telefon == '011999888'
                assert updated_firma.email == 'updated@firma.rs'
                assert updated_firma.pib == sample_firma.pib  # PIB should not change

    def test_pib_readonly_in_edit_form(self, client, admin_user, sample_firma):
        """Test that PIB field is readonly in edit form."""
        with client:
            # Login as admin
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'admin123'
            })

            # GET edit form
            response = client.get(f'/admin/firme/{sample_firma.id}/izmeni')
            assert response.status_code == 200

            # Check for readonly attribute in PIB field
            response_text = response.data.decode('utf-8')
            assert 'readonly' in response_text
            assert sample_firma.pib in response_text

    def test_admin_access_to_edit_route(self, client, admin_user, sample_firma):
        """Test that admin users can access edit route."""
        # Note: Pausalac access control is tested in test_tenant_isolation.py
        with client:
            # Login as admin
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'admin123'
            })

            # Verify admin can access edit form
            response = client.get(f'/admin/firme/{sample_firma.id}/izmeni')
            assert response.status_code == 200
            assert b'Izmeni' in response.data

    def test_pib_cannot_be_changed_via_post_request(self, app, client, admin_user, sample_firma):
        """Test that PIB immutability is enforced on backend (SEC-001)."""
        with client:
            # Login as admin
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'admin123'
            })

            original_pib = sample_firma.pib

            # Attempt to change PIB via direct POST request (bypassing readonly form field)
            response = client.post(f'/admin/firme/{sample_firma.id}/izmeni', data={
                'pib': '99999999',  # Attempt to change PIB
                'naziv': 'Test Firma DOO',
                'maticni_broj': '87654321',
                'adresa': 'Test Ulica',
                'broj': '10',
                'postanski_broj': '11000',
                'mesto': 'Beograd',
                'drzava': 'Srbija',
                'telefon': '011234567',
                'email': 'test@firma.rs',
                'dinarski_racuni_json': json.dumps([{'banka': 'Banka', 'broj': '123-456789-10'}]),
                'devizni_racuni_json': json.dumps([]),
                'prefiks_fakture': 'INV',
                'sufiks_fakture': '2025',
                'pdv_kategorija': 'SS',
                'sifra_osnova': 'PDV-RS-33'
            }, follow_redirects=False)

            # Backend should reject the request and return 200 with error message (not redirect)
            assert response.status_code == 200
            assert 'PIB ne može biti izmenjen' in response.data.decode('utf-8')

            # Verify PIB has NOT changed in database
            with app.app_context():
                firma = db.session.get(PausalnFirma, sample_firma.id)
                assert firma.pib == original_pib
                assert firma.pib != '99999999'


class TestPausalnFirmaDeleteFlow:
    """Test complete delete flow for PausalnFirma."""

    def test_admin_sees_delete_button_on_detail_view(self, client, admin_user, sample_firma):
        """Test that admin sees delete button on detail view."""
        with client:
            # Login as admin
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'admin123'
            })

            # GET detail view
            response = client.get(f'/admin/firme/{sample_firma.id}')
            assert response.status_code == 200
            assert 'Obriši'.encode('utf-8') in response.data
            assert b'deleteFirmaModal' in response.data  # Confirmation modal present

    def test_admin_sees_confirmation_modal(self, client, admin_user, sample_firma):
        """Test that confirmation modal is displayed before delete."""
        with client:
            # Login as admin
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'admin123'
            })

            # GET detail view
            response = client.get(f'/admin/firme/{sample_firma.id}')
            assert response.status_code == 200

            response_text = response.data.decode('utf-8')
            assert 'Da li ste sigurni' in response_text
            assert sample_firma.naziv in response_text
            assert 'povezane fakture, komitente i korisnike' in response_text

    def test_admin_can_delete_firma(self, app, client, admin_user, sample_firma):
        """Test that admin can delete firma and be redirected to firme list."""
        with client:
            # Login as admin
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'admin123'
            })

            firma_id = sample_firma.id

            # POST delete (CSRF is disabled in testing config)
            response = client.post(f'/admin/firme/{firma_id}/obrisi', follow_redirects=True)

            assert response.status_code == 200
            assert 'uspešno obrisana' in response.data.decode('utf-8')

            # Verify firma is deleted from database
            with app.app_context():
                deleted_firma = db.session.get(PausalnFirma, firma_id)
                assert deleted_firma is None

    def test_admin_access_to_delete_route(self, app, client, admin_user, sample_firma):
        """Test that admin users can access delete route."""
        # Note: Pausalac access control is tested in test_tenant_isolation.py
        with client:
            # Login as admin
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'admin123'
            })

            firma_id = sample_firma.id

            # Verify admin can successfully delete firma
            response = client.post(f'/admin/firme/{firma_id}/obrisi', follow_redirects=True)
            assert response.status_code == 200
            assert 'uspešno obrisana' in response.data.decode('utf-8')

    def test_delete_error_handling(self, client, admin_user):
        """Test error handling when trying to delete non-existent firma."""
        with client:
            # Login as admin
            client.post('/login', data={
                'email': admin_user.email,
                'password': 'admin123'
            })

            # Try to delete non-existent firma
            response = client.post('/admin/firme/99999/obrisi')
            assert response.status_code == 404


@pytest.fixture
def sample_firma(app):
    """Create a sample PausalnFirma for testing."""
    with app.app_context():
        firma = PausalnFirma(
            pib='12345678',
            maticni_broj='87654321',
            naziv='Test Firma DOO',
            adresa='Kneza Milosa',
            broj='10',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            telefon='011234567',
            email='test@firma.rs',
            dinarski_racuni=[{'banka': 'Komercijalna Banka', 'broj': '123-456789-10'}],
            devizni_racuni=[{'banka': 'Komercijalna Banka', 'iban': 'RS35260005601001611379', 'swift': 'KOBBRSBG'}],
            prefiks_fakture='INV',
            sufiks_fakture='2025'
        )
        db.session.add(firma)
        db.session.commit()
        firma_id = firma.id

    # Return a simple object with just the ID to avoid session issues
    class FirmaRef:
        def __init__(self, id, pib, naziv):
            self.id = id
            self.pib = pib
            self.naziv = naziv

    return FirmaRef(firma_id, '12345678', 'Test Firma DOO')


@pytest.fixture
def admin_user(app, sample_firma):
    """Create an admin user for testing."""
    with app.app_context():
        admin = User(
            email='admin@test.com',
            full_name='Admin User',
            password_hash='pbkdf2:sha256:600000$test$dummy_hash',
            role='admin',
            firma_id=sample_firma.id
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    class UserRef:
        def __init__(self, id, email):
            self.id = id
            self.email = email

    return UserRef(admin_id, 'admin@test.com')


@pytest.fixture
def pausalac_user(app, sample_firma):
    """Create a pausalac user for testing."""
    with app.app_context():
        pausalac = User(
            email='pausalac@test.com',
            full_name='Pausalac User',
            password_hash='pbkdf2:sha256:600000$test$dummy_hash',
            role='pausalac',
            firma_id=sample_firma.id
        )
        pausalac.set_password('pausalac123')
        db.session.add(pausalac)
        db.session.commit()
        pausalac_id = pausalac.id

    class UserRef:
        def __init__(self, id, email):
            self.id = id
            self.email = email

    return UserRef(pausalac_id, 'pausalac@test.com')
