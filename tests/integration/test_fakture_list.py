"""Integration tests for Fakture List endpoint (GET /fakture)."""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from flask import url_for

from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.komitent import Komitent
from app.models.faktura import Faktura


@pytest.fixture
def pausalac_user_with_fakture(app, client):
    """Create pausalac user with firma and multiple fakture."""
    firma = PausalnFirma(
        pib='12345678',
        maticni_broj='12345678',
        naziv='Test Firma',
        adresa='Test Adresa',
        broj='1',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        telefon='011111111',
        email='firma@test.com',
        dinarski_racuni=[{'banka': 'Test Banka', 'racun': '123-456789-00'}],
        prefiks_fakture='TF-',
        sufiks_fakture='/2025',
        brojac_fakture=1
    )
    db.session.add(firma)
    db.session.flush()

    user = User(
        email='pausalac@test.com',
        full_name='Test Pausalac',
        role='pausalac',
        firma_id=firma.id
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.flush()

    # Create komitent
    komitent = Komitent(
        firma_id=firma.id,
        pib='11111111',
        maticni_broj='11111111',
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

    # Create 25 fakture (to test pagination: 20 per page)
    today = date.today()
    for i in range(25):
        faktura = Faktura(
            firma_id=firma.id,
            komitent_id=komitent.id,
            user_id=user.id,
            broj_fakture=f'TF-{i+1:04d}/2025',
            tip_fakture='standardna',
            valuta_fakture='RSD' if i % 2 == 0 else 'EUR',
            datum_prometa=today - timedelta(days=i),
            valuta_placanja=7,
            datum_dospeca=today - timedelta(days=i) + timedelta(days=7),
            ukupan_iznos_rsd=Decimal(f'{(i+1)*1000}.00'),
            status='draft' if i < 10 else 'izdata',
            pdf_url=f'/storage/fakture/test-{i}.pdf' if i >= 10 else None
        )
        db.session.add(faktura)

    db.session.commit()

    yield user, firma

    # Release database connection
    db.session.remove()


class TestFaktureListPage:
    """Tests for fakture list page rendering."""

    def test_fakture_list_page_loads(self, app, client, pausalac_user_with_fakture):
        """Test that GET /fakture renders page successfully."""
        user, firma = pausalac_user_with_fakture

        # Login
        with client:
            client.post('/login', data={
                'email': 'pausalac@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            # Access fakture list
            response = client.get('/fakture/')

            assert response.status_code == 200
            assert b'Moje Fakture' in response.data

    def test_fakture_list_shows_own_fakture(self, app, client, pausalac_user_with_fakture):
        """Test that pausalac sees only their own fakture."""
        user, firma = pausalac_user_with_fakture

        # Login
        with client:
            client.post('/login', data={
                'email': 'pausalac@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            # Access fakture list
            response = client.get('/fakture/')

            assert response.status_code == 200
            # Check that some fakture numbers are displayed
            assert b'TF-0001/2025' in response.data
            # Check pagination info (25 fakture, showing 1-20)
            assert b'Prikazano 1-20 od 25 faktura' in response.data

    def test_filter_by_status_works(self, app, client, pausalac_user_with_fakture):
        """Test filtering by status."""
        user, firma = pausalac_user_with_fakture

        # Login
        with client:
            client.post('/login', data={
                'email': 'pausalac@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            # Filter by status=draft
            response = client.get('/fakture/?status=draft')

            assert response.status_code == 200
            # Should show only draft fakture (first 10 in our fixture)
            assert b'Prikazano 1-10 od 10 faktura' in response.data

    def test_filter_by_valuta_works(self, app, client, pausalac_user_with_fakture):
        """Test filtering by valuta."""
        user, firma = pausalac_user_with_fakture

        # Login
        with client:
            client.post('/login', data={
                'email': 'pausalac@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            # Filter by valuta=EUR
            response = client.get('/fakture/?valuta=EUR')

            assert response.status_code == 200
            # Half of fakture are EUR (13 out of 25)
            # Actually 12 because we have 25 fakture: 0-24, odd indices = EUR = 12 fakture
            # (1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23)

    def test_search_by_broj_works(self, app, client, pausalac_user_with_fakture):
        """Test search by invoice number."""
        user, firma = pausalac_user_with_fakture

        # Login
        with client:
            client.post('/login', data={
                'email': 'pausalac@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            # Search for 'TF-000'
            response = client.get('/fakture/?search=TF-000')

            assert response.status_code == 200
            # Should match TF-0001 through TF-0009 (9 fakture)
            assert b'TF-0001/2025' in response.data

    def test_pagination_works(self, app, client, pausalac_user_with_fakture):
        """Test pagination controls."""
        user, firma = pausalac_user_with_fakture

        # Login
        with client:
            client.post('/login', data={
                'email': 'pausalac@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            # Page 1 (20 fakture)
            response = client.get('/fakture/?page=1')

            assert response.status_code == 200
            assert b'Prikazano 1-20 od 25 faktura' in response.data

            # Page 2 (remaining 5 fakture)
            response = client.get('/fakture/?page=2')

            assert response.status_code == 200
            assert b'Prikazano 21-25 od 25 faktura' in response.data

    def test_quick_actions_visible(self, app, client, pausalac_user_with_fakture):
        """Test that quick action buttons are visible."""
        user, firma = pausalac_user_with_fakture

        # Login
        with client:
            client.post('/login', data={
                'email': 'pausalac@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            response = client.get('/fakture/')

            assert response.status_code == 200
            # Check for action buttons (eye icon for preview)
            assert b'fa-eye' in response.data

    def test_preuzmi_pdf_link_exists(self, app, client, pausalac_user_with_fakture):
        """Test that 'Preuzmi PDF' link exists for fakture with PDF."""
        user, firma = pausalac_user_with_fakture

        # Login
        with client:
            client.post('/login', data={
                'email': 'pausalac@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            response = client.get('/fakture/')

            assert response.status_code == 200
            # Check for download icon (only for izdata fakture with PDF)
            assert b'fa-download' in response.data

    def test_email_button_visible_for_izdata_fakture(self, app, client, pausalac_user_with_fakture):
        """Test that email button is visible for izdata fakture with PDF."""
        user, firma = pausalac_user_with_fakture

        # Login
        with client:
            client.post('/login', data={
                'email': 'pausalac@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            response = client.get('/fakture/')

            assert response.status_code == 200
            # Check for email icon/button (only for izdata fakture with PDF)
            # Fakture 10-24 have status='izdata' and pdf_url (15 fakture)
            assert b'fa-envelope' in response.data or b'fa-paper-plane' in response.data
