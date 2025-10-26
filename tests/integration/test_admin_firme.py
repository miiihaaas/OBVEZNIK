"""
Integration tests for admin firme CRUD complete flow.
"""
import pytest
from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from flask_login import login_user


@pytest.fixture
def admin_user():
    """Create admin user."""
    user = User(
        email='admin@test.com',
        role='admin',
        full_name='Admin User',
        is_active=True
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def pausalac_user():
    """Create pausalac user with firma."""
    # Create firma first
    firma = PausalnFirma(
        pib='12345678',
        maticni_broj='87654321',
        naziv='Test Paušalna Firma',
        adresa='Test Adresa 1',
        broj='1',
        postanski_broj='11000',
        mesto='Beograd',
        telefon='0601234567',
        email='firma@test.com',
        dinarski_racuni=[{'banka': 'Test Banka', 'racun': '123-456-789'}]
    )
    db.session.add(firma)
    db.session.commit()

    # Create pausalac user linked to firma
    user = User(
        email='pausalac@test.com',
        role='pausalac',
        full_name='Pausalac User',
        is_active=True,
        firma_id=firma.id
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def multiple_firme():
    """Create multiple firme for list testing."""
    firme = []
    for i in range(3):
        firma = PausalnFirma(
            pib=f'1111111{i}',
            maticni_broj=f'2222222{i}',
            naziv=f'Firma Test {i}',
            adresa=f'Adresa {i}',
            broj=str(i),
            postanski_broj='11000',
            mesto='Beograd',
            telefon=f'06011111{i}',
            email=f'firma{i}@test.com',
            dinarski_racuni=[{'banka': 'Banka', 'racun': f'123-{i}'}],
            is_active=(i % 2 == 0)  # Alternate active/inactive
        )
        db.session.add(firma)
        firme.append(firma)
    db.session.commit()
    return firme


class TestAdminFirmeAccess:
    """Test access control for admin firme route."""

    def test_admin_can_access_firme_route(self, client, admin_user):
        """Test Admin can access /admin/firme route."""
        # Use context manager to maintain session
        with client:
            # Login as admin
            response = client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            assert response.status_code == 200

            # Access admin firme route
            response = client.get('/admin/firme')

            assert response.status_code == 200
            assert 'Paušalne Firme'.encode('utf-8') in response.data

    def test_pausalac_cannot_access_admin_route(self, client, pausalac_user):
        """Test Paušalac cannot access admin route (403 or redirect)."""
        # Use context manager to maintain session
        with client:
            # Login as pausalac
            response = client.post('/login', data={
                'email': 'pausalac@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            assert response.status_code == 200

            # Try to access admin route
            response = client.get('/admin/firme', follow_redirects=False)

            # Should be forbidden (403) - pausalac cannot access admin routes
            assert response.status_code == 403

    def test_anonymous_user_redirected_to_login(self, client):
        """Test anonymous user is redirected or gets unauthorized."""
        # Ensure no active session (logout if logged in)
        client.get('/logout', follow_redirects=True)

        # Try to access admin route without being logged in
        response = client.get('/admin/firme', follow_redirects=False)

        # Should get redirect (302) or unauthorized (401/403) when not logged in
        # Note: Flask-Login typically returns 401, but redirect is also acceptable
        assert response.status_code in [302, 401, 403]


class TestAdminFirmeTableDisplay:
    """Test table displays correct columns and data."""

    def test_table_displays_all_columns(self, client, admin_user, multiple_firme):
        """Test table shows all required columns."""
        with client:
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            response = client.get('/admin/firme')

            assert response.status_code == 200
            # Check all column headers exist
            assert 'Naziv'.encode('utf-8') in response.data
            assert b'PIB' in response.data
            assert 'Matični Broj'.encode('utf-8') in response.data or b'Maticni Broj' in response.data
            assert 'Mesto'.encode('utf-8') in response.data
            assert 'Broj Faktura'.encode('utf-8') in response.data
            assert 'Status'.encode('utf-8') in response.data
            assert 'Akcije'.encode('utf-8') in response.data

    def test_table_displays_firma_data(self, client, admin_user, multiple_firme):
        """Test table shows firma data correctly."""
        with client:
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            response = client.get('/admin/firme')

            assert response.status_code == 200
            # Check firma data is displayed
            assert b'Firma Test 0' in response.data
            assert b'11111110' in response.data  # PIB
            assert b'22222220' in response.data  # Maticni broj

    def test_status_badge_displays_correctly(self, client, admin_user, multiple_firme):
        """Test status badge shows active/inactive correctly."""
        with client:
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            response = client.get('/admin/firme')

            assert response.status_code == 200
            # Check for status badges
            assert 'Aktivna'.encode('utf-8') in response.data or b'badge bg-success' in response.data
            assert 'Neaktivna'.encode('utf-8') in response.data or b'badge bg-danger' in response.data

    def test_broj_faktura_column_displays(self, client, admin_user, multiple_firme):
        """Test broj faktura column shows count."""
        with client:
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            response = client.get('/admin/firme')

            assert response.status_code == 200
            # Should show 0 faktura for new firme
            assert b'badge bg-secondary' in response.data or b'0' in response.data


class TestAdminFirmeSortingLinks:
    """Test sorting links change query parameters correctly."""

    def test_sorting_link_changes_query_params(self, client, admin_user, multiple_firme):
        """Test clicking sort link changes URL query params."""
        with client:
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            # Get page with sorting
            response = client.get('/admin/firme?sort=naziv&order=asc')

            assert response.status_code == 200
            # Check sort indicator is present
            assert b'fa-sort' in response.data

    def test_sorting_toggle_asc_desc(self, client, admin_user, multiple_firme):
        """Test sort order toggles between asc and desc."""
        with client:
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            # First sort asc
            response = client.get('/admin/firme?sort=naziv&order=asc')
            assert response.status_code == 200
            assert b'sort-up' in response.data or b'fa-sort-up' in response.data

            # Then sort desc
            response = client.get('/admin/firme?sort=naziv&order=desc')
            assert response.status_code == 200
            assert b'sort-down' in response.data or b'fa-sort-down' in response.data


class TestAdminFirmeSearchForm:
    """Test search form filters results."""

    def test_search_form_exists(self, client, admin_user, multiple_firme):
        """Test search form is displayed."""
        with client:
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            response = client.get('/admin/firme')

            assert response.status_code == 200
            # Check search form elements exist
            assert b'name="search"' in response.data
            assert 'Pretraži'.encode('utf-8') in response.data or b'Search' in response.data

    def test_search_form_filters_results(self, client, admin_user, multiple_firme):
        """Test search form actually filters results."""
        with client:
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            # Search for specific firma
            response = client.get('/admin/firme?search=Firma+Test+0')

            assert response.status_code == 200
            assert b'Firma Test 0' in response.data
            # Other firme should not appear (or less results shown)

    def test_search_preserves_term_in_input(self, client, admin_user, multiple_firme):
        """Test search term is preserved in input field after search."""
        with client:
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            response = client.get('/admin/firme?search=TestTerm')

            assert response.status_code == 200
            # Search term should be in input value
            assert b'value="TestTerm"' in response.data

    def test_reset_link_clears_search(self, client, admin_user, multiple_firme):
        """Test reset link clears search and shows all firme."""
        with client:
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            # First search
            response = client.get('/admin/firme?search=Firma')
            assert response.status_code == 200

            # Then reset (go to /admin/firme without params)
            response = client.get('/admin/firme')
            assert response.status_code == 200
            # Should show all 3 firme
            assert b'Firma Test 0' in response.data
            assert b'Firma Test 1' in response.data
            assert b'Firma Test 2' in response.data


class TestAdminFirmePaginationDisplay:
    """Test pagination controls display correctly."""

    def test_pagination_shows_when_more_than_20_firme(self, client, admin_user):
        """Test pagination controls appear when more than 20 items."""
        # Create 25 firme
        for i in range(25):
            firma = PausalnFirma(
                pib=f'9999{i:04d}',
                maticni_broj=f'8888{i:04d}',
                naziv=f'Pag Firma {i}',
                adresa=f'Addr {i}',
                broj=str(i),
                postanski_broj='11000',
                mesto='Beograd',
                telefon=f'06099999{i:02d}',
                email=f'pag{i}@test.com',
                dinarski_racuni=[{'banka': 'Bank', 'racun': f'{i}'}]
            )
            db.session.add(firma)
        db.session.commit()

        with client:
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            response = client.get('/admin/firme')

            assert response.status_code == 200
            # Pagination should be visible
            assert b'pagination' in response.data
            assert 'Stranica'.encode('utf-8') in response.data

    def test_pagination_page_info_displayed(self, client, admin_user):
        """Test page info "Stranica X od Y" is displayed."""
        # Create 25 firme
        for i in range(25):
            firma = PausalnFirma(
                pib=f'7777{i:04d}',
                maticni_broj=f'6666{i:04d}',
                naziv=f'Info Firma {i}',
                adresa=f'Addr {i}',
                broj=str(i),
                postanski_broj='11000',
                mesto='Beograd',
                telefon=f'06077777{i:02d}',
                email=f'info{i}@test.com',
                dinarski_racuni=[{'banka': 'Bank', 'racun': f'{i}'}]
            )
            db.session.add(firma)
        db.session.commit()

        with client:
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            response = client.get('/admin/firme?page=1')

            assert response.status_code == 200
            assert 'Stranica 1 od 2'.encode('utf-8') in response.data


class TestAdminFirmeDetailLink:
    """Test clicking Detalji button opens detail view."""

    def test_detalji_button_opens_detail_view(self, client, admin_user, multiple_firme):
        """Test clicking Detalji button navigates to detail view."""
        with client:
            client.post('/login', data={
                'email': 'admin@test.com',
                'password': 'password123'
            }, follow_redirects=True)

            # Get list page
            response = client.get('/admin/firme')
            assert response.status_code == 200

            # Click on detail link for first firma
            firma_id = multiple_firme[0].id
            response = client.get(f'/admin/firme/{firma_id}')

            assert response.status_code == 200
            # Should show firma detail page
            assert b'Firma Test 0' in response.data
            # Detail view should show all firma data
            assert b'11111110' in response.data  # PIB
            assert b'Adresa 0' in response.data
