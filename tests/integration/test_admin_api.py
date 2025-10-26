"""Integration tests for Admin API endpoints (autocomplete, lazy load)."""
import pytest
from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma


@pytest.fixture
def admin_user(app):
    """Create an admin user for testing."""
    user = User(
        email='admin@test.com',
        full_name='Test Admin',
        role='admin'
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def pausalac_user(app):
    """Create a pausalac user for testing."""
    firma = PausalnFirma(
        pib='123456789',
        maticni_broj='12345678',
        naziv='Test Firma',
        adresa='Test Address',
        broj='1',
        mesto='Belgrade',
        postanski_broj='11000',
        email='test@firma.com',
        telefon='+381111111111',
        dinarski_racuni=['111-111111-11']
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
    db.session.commit()
    return user


@pytest.fixture
def multiple_firme(app):
    """Create multiple firme for testing search and pagination."""
    firme = [
        PausalnFirma(
            pib=f'{100000000 + i}',  # PIB must be 9 digits
            maticni_broj=f'{10000000 + i}',  # 8 digits
            naziv=f'Firma {chr(65 + i)}',  # Firma A, Firma B, ...
            adresa='Test Address',
            broj='1',
            mesto='Belgrade',
            postanski_broj='11000',
            email=f'firma{i}@test.com',
            telefon='+381111111111',
            dinarski_racuni=['111-111111-11']
        )
        for i in range(25)  # Create 25 firme
    ]
    db.session.add_all(firme)
    db.session.commit()
    return firme


class TestFirmeSearchAPI:
    """Test /api/admin/firme/search endpoint."""

    def test_admin_can_search_firme(self, client, admin_user, multiple_firme):
        """Test admin can search firme via API."""
        # Login as admin
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Search for firme
        response = client.get('/api/admin/firme/search')
        assert response.status_code == 200

        data = response.get_json()
        assert 'firme' in data
        assert 'total' in data
        assert 'has_more' in data
        assert data['total'] == 25
        assert len(data['firme']) == 20  # Default limit

    def test_admin_can_search_with_query(self, client, admin_user, multiple_firme):
        """Test admin can search firme with query parameter."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Search for "Firma A"
        response = client.get('/api/admin/firme/search?q=Firma A')
        assert response.status_code == 200

        data = response.get_json()
        assert data['total'] == 1
        assert data['firme'][0]['naziv'] == 'Firma A'

    def test_admin_can_search_by_pib(self, client, admin_user, multiple_firme):
        """Test admin can search firme by PIB."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Search by PIB (first firma has PIB 100000000)
        response = client.get('/api/admin/firme/search?q=100000000')
        assert response.status_code == 200

        data = response.get_json()
        assert data['total'] >= 1
        assert data['firme'][0]['pib'] == '100000000'

    def test_admin_can_limit_results(self, client, admin_user, multiple_firme):
        """Test admin can limit search results."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Limit to 10 results
        response = client.get('/api/admin/firme/search?limit=10')
        assert response.status_code == 200

        data = response.get_json()
        assert len(data['firme']) == 10
        assert data['has_more'] is True

    def test_admin_can_paginate_results(self, client, admin_user, multiple_firme):
        """Test admin can paginate search results."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Get first page
        response = client.get('/api/admin/firme/search?limit=10&offset=0')
        assert response.status_code == 200
        first_page = response.get_json()
        assert len(first_page['firme']) == 10

        # Get second page
        response = client.get('/api/admin/firme/search?limit=10&offset=10')
        assert response.status_code == 200
        second_page = response.get_json()
        assert len(second_page['firme']) == 10

        # Ensure different results
        assert first_page['firme'][0]['id'] != second_page['firme'][0]['id']

    def test_max_limit_is_100(self, client, admin_user, multiple_firme):
        """Test API enforces max limit of 100 results."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        # Request 200 results (should be capped at 100)
        response = client.get('/api/admin/firme/search?limit=200')
        assert response.status_code == 200

        data = response.get_json()
        assert len(data['firme']) <= 100

    def test_pausalac_cannot_access_api(self, client, pausalac_user):
        """Test pausalac cannot access admin API endpoint."""
        client.post('/login', data={
            'email': 'pausalac@test.com',
            'password': 'password123'
        })

        response = client.get('/api/admin/firme/search')
        assert response.status_code == 403

    def test_unauthenticated_user_cannot_access_api(self, client):
        """Test unauthenticated user cannot access admin API."""
        response = client.get('/api/admin/firme/search', follow_redirects=False)
        # Flask-Login redirects to login page (302) instead of 401
        assert response.status_code == 302

    def test_empty_search_returns_all_firme(self, client, admin_user, multiple_firme):
        """Test empty search query returns all firme."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        response = client.get('/api/admin/firme/search?q=')
        assert response.status_code == 200

        data = response.get_json()
        assert data['total'] == 25

    def test_no_results_returns_empty_list(self, client, admin_user, multiple_firme):
        """Test search with no matches returns empty list."""
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        })

        response = client.get('/api/admin/firme/search?q=NonexistentFirma')
        assert response.status_code == 200

        data = response.get_json()
        assert data['total'] == 0
        assert data['firme'] == []
        assert data['has_more'] is False
