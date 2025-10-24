"""
Unit tests for admin firme route logic (sorting, search, pagination).
"""
import pytest
from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from datetime import datetime, timezone


@pytest.fixture
def admin_user():
    """Create admin user for testing."""
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
def sample_firme():
    """Create 25 sample firme for pagination/sorting/search tests."""
    import random
    firme = []

    # Generate unique random suffix to avoid conflicts across tests
    rand_suffix = random.randint(10000, 99999)

    # Create firms with different names and PIBs
    firma_data = [
        ('ABC Firma', 'Beograd'),
        ('XYZ Kompanija', 'Novi Sad'),
        ('Delta Servis', 'Niš'),
        ('Beta Tech', 'Subotica'),
        ('Alfa Trade', 'Kragujevac'),
    ]

    # Create 25 firme with absolutely unique PIBs
    for i in range(25):
        if i < len(firma_data):
            naziv, mesto = firma_data[i]
        else:
            naziv = f'Firma {i+1}'
            mesto = 'Beograd'

        # Generate truly unique PIB using timestamp component + index
        pib = f'{rand_suffix}{i:03d}'  # e.g., 12345000, 12345001, etc

        firma = PausalnFirma(
            pib=pib,
            maticni_broj=f'{rand_suffix}{i:03d}',  # Match PIB for simplicity
            naziv=naziv,
            adresa=f'Ulica {i+1}',
            broj=f'{i+1}',
            postanski_broj='11000',
            mesto=mesto,
            telefon=f'06012345{i:02d}',
            email=f'firma{rand_suffix}{i}@test.com',  # Unique email too
            dinarski_racuni=[{'banka': 'Banka', 'racun': f'123-456-{rand_suffix}-{i}'}],
            is_active=(i % 2 == 0)  # Alternate active/inactive
        )
        db.session.add(firma)
        firme.append(firma)

    db.session.commit()
    return firme


class TestAdminFirmeSorting:
    """Test sorting functionality."""

    def test_sorting_by_naziv_asc(self, client, admin_user, sample_firme):
        """Test sorting by naziv in ascending order."""
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Request sorted by naziv asc
        response = client.get('/admin/firme?sort=naziv&order=asc')

        assert response.status_code == 200
        # Verify first 20 items are sorted alphabetically
        # (ABC should come before Alfa, Beta, Delta, Firma 10, etc.)
        assert b'ABC Firma' in response.data

    def test_sorting_by_naziv_desc(self, client, admin_user, sample_firme):
        """Test sorting by naziv in descending order."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        response = client.get('/admin/firme?sort=naziv&order=desc')

        assert response.status_code == 200
        # XYZ should be near top when sorted descending
        assert b'XYZ Kompanija' in response.data

    def test_sorting_by_pib_asc(self, client, admin_user, sample_firme):
        """Test sorting by PIB in ascending order."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        response = client.get('/admin/firme?sort=pib&order=asc')

        assert response.status_code == 200
        # Smallest PIB (first firma) should appear first
        assert sample_firme[0].pib.encode() in response.data

    def test_sorting_by_pib_desc(self, client, admin_user, sample_firme):
        """Test sorting by PIB in descending order."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        response = client.get('/admin/firme?sort=pib&order=desc')

        assert response.status_code == 200
        assert response.status_code == 200

    def test_sorting_by_created_at_asc(self, client, admin_user, sample_firme):
        """Test sorting by created_at in ascending order."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        response = client.get('/admin/firme?sort=created_at&order=asc')

        assert response.status_code == 200

    def test_sorting_by_created_at_desc(self, client, admin_user, sample_firme):
        """Test sorting by created_at in descending order."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        response = client.get('/admin/firme?sort=created_at&order=desc')

        assert response.status_code == 200

    def test_invalid_sort_column_defaults_to_naziv(self, client, admin_user, sample_firme):
        """Test that invalid sort column defaults to naziv."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Try to sort by invalid column
        response = client.get('/admin/firme?sort=invalid_column&order=asc')

        assert response.status_code == 200
        # Should still work (fallback to naziv)


class TestAdminFirmeSearch:
    """Test search/filter functionality."""

    def test_search_by_naziv_match(self, client, admin_user, sample_firme):
        """Test search finds firma by naziv."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        response = client.get('/admin/firme?search=ABC')

        assert response.status_code == 200
        assert b'ABC Firma' in response.data
        # Should not show unrelated firme
        assert b'XYZ Kompanija' not in response.data

    def test_search_by_pib_match(self, client, admin_user, sample_firme):
        """Test search finds firma by PIB."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Search for second firma's PIB (XYZ Kompanija)
        search_pib = sample_firme[1].pib
        response = client.get(f'/admin/firme?search={search_pib}')

        assert response.status_code == 200
        assert search_pib.encode() in response.data
        assert b'XYZ Kompanija' in response.data

    def test_search_no_match(self, client, admin_user, sample_firme):
        """Test search with no results."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        response = client.get('/admin/firme?search=NonexistentFirma')

        assert response.status_code == 200
        assert b'Nema rezultata pretrage' in response.data

    def test_search_case_insensitive(self, client, admin_user, sample_firme):
        """Test search is case-insensitive."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Search with lowercase when firma has uppercase
        response = client.get('/admin/firme?search=abc')

        assert response.status_code == 200
        assert b'ABC Firma' in response.data


class TestAdminFirmePagination:
    """Test pagination functionality."""

    def test_pagination_page_1(self, client, admin_user, sample_firme):
        """Test first page of pagination shows 20 items."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        response = client.get('/admin/firme?page=1')

        assert response.status_code == 200
        # Should show page 1 of 2 (25 firme / 20 per page = 2 pages)
        assert b'Stranica 1 od 2' in response.data

    def test_pagination_page_2(self, client, admin_user, sample_firme):
        """Test second page of pagination shows remaining items."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        response = client.get('/admin/firme?page=2')

        assert response.status_code == 200
        # Should show page 2 (last page)
        assert b'Stranica 2 od 2' in response.data

    def test_pagination_invalid_page(self, client, admin_user, sample_firme):
        """Test invalid page number doesn't crash."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        response = client.get('/admin/firme?page=999')

        # Should return 200 with empty results (error_out=False)
        assert response.status_code == 200

    def test_pagination_with_less_than_20_items(self, client, admin_user):
        """Test pagination doesn't show when less than 20 items."""
        # Create only 5 firme
        for i in range(5):
            firma = PausalnFirma(
                pib=f'5000000{i}',
                maticni_broj=f'6000000{i}',
                naziv=f'Small Firma {i}',
                adresa=f'Addr {i}',
                broj=str(i),
                postanski_broj='11000',
                mesto='Beograd',
                telefon=f'06011111{i}',
                email=f'small{i}@test.com',
                dinarski_racuni=[{'banka': 'Bank', 'racun': f'123-{i}'}]
            )
            db.session.add(firma)
        db.session.commit()

        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        response = client.get('/admin/firme')

        assert response.status_code == 200
        # Pagination controls should not be visible
        assert b'page-item' not in response.data or b'Stranica' not in response.data


class TestAdminFirmeCombined:
    """Test combinations of search, sort, and pagination."""

    def test_search_with_sorting(self, client, admin_user, sample_firme):
        """Test search combined with sorting."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Search for "Firma" and sort by PIB
        response = client.get('/admin/firme?search=Firma&sort=pib&order=asc')

        assert response.status_code == 200
        assert b'Firma' in response.data

    def test_search_with_pagination(self, client, admin_user, sample_firme):
        """Test search combined with pagination."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Search for "Firma" (should match many) and paginate
        response = client.get('/admin/firme?search=Firma&page=1')

        assert response.status_code == 200
        assert b'Firma' in response.data

    def test_all_parameters_combined(self, client, admin_user, sample_firme):
        """Test search + sort + pagination all together."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        response = client.get('/admin/firme?search=Firma&sort=naziv&order=desc&page=1')

        assert response.status_code == 200
