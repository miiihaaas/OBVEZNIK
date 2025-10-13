"""Unit tests for access control decorators and query helpers."""
import pytest
from flask import Flask
from flask_login import login_user, logout_user
from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.faktura import Faktura
from app.utils.decorators import admin_required
from app.utils.query_helpers import get_user_firma_id, filter_by_firma


def test_admin_required_decorator_unauthenticated(app):
    """Test that @admin_required returns 401 for unauthenticated users."""
    with app.test_request_context():
        # Create a mock route with @admin_required
        @admin_required
        def mock_admin_route():
            return "Admin content"

        # Call the decorated function without authentication
        with pytest.raises(Exception) as exc_info:
            mock_admin_route()

        # Verify 401 Unauthorized is raised
        assert exc_info.value.code == 401


def test_admin_required_decorator_pausalac(app):
    """Test that @admin_required returns 403 for pausalac users."""
    with app.test_request_context():
        # Create pausaln firma first
        firma = PausalnFirma(
            pib='123456789',
            naziv='Test Firma',
            adresa='Test Adresa',
            broj='1',
            mesto='Beograd',
            postanski_broj='11000',
            maticni_broj='12345678',
            telefon='011234567',
            email='test@firma.rs',
            dinarski_racuni=[{'racun': '123-456-789', 'banka': 'Test Banka'}]
        )
        db.session.add(firma)
        db.session.commit()

        # Create pausalac user
        pausalac = User(
            email='pausalac@test.com',
            full_name='Test Pausalac',
            role='pausalac',
            firma_id=firma.id
        )
        pausalac.set_password('password123')
        db.session.add(pausalac)
        db.session.commit()

        # Login as pausalac
        login_user(pausalac)

        # Create a mock route with @admin_required
        @admin_required
        def mock_admin_route():
            return "Admin content"

        # Call the decorated function
        with pytest.raises(Exception) as exc_info:
            mock_admin_route()

        # Verify 403 Forbidden is raised
        assert exc_info.value.code == 403

        # Cleanup
        logout_user()


def test_admin_required_decorator_admin(app):
    """Test that @admin_required allows access for admin users."""
    with app.test_request_context():
        # Create admin user
        admin = User(
            email='admin@test.com',
            full_name='Test Admin',
            role='admin',
            firma_id=None
        )
        admin.set_password('password123')
        db.session.add(admin)
        db.session.commit()

        # Login as admin
        login_user(admin)

        # Create a mock route with @admin_required
        @admin_required
        def mock_admin_route():
            return "Admin content"

        # Call the decorated function
        result = mock_admin_route()

        # Verify access is granted
        assert result == "Admin content"

        # Cleanup
        logout_user()


def test_login_required_redirects_to_login(app, client):
    """Test that @login_required redirects unauthenticated users to login page."""
    # Attempt to access protected route without authentication
    response = client.get('/dashboard', follow_redirects=False)

    # Should redirect to login page
    assert response.status_code == 302
    assert '/login' in response.location


def test_get_user_firma_id_admin(app):
    """Test that get_user_firma_id() returns None for Admin user."""
    with app.test_request_context():
        # Create admin user
        admin = User(
            email='admin@test.com',
            full_name='Test Admin',
            role='admin',
            firma_id=None
        )
        admin.set_password('password123')
        db.session.add(admin)
        db.session.commit()

        # Login as admin
        login_user(admin)

        # Get firma_id
        firma_id = get_user_firma_id()

        # Admin should return None (god mode)
        assert firma_id is None

        # Cleanup
        logout_user()


def test_get_user_firma_id_pausalac(app):
    """Test that get_user_firma_id() returns firma_id for Pausalac user."""
    with app.test_request_context():
        # Create pausaln firma first
        firma = PausalnFirma(
            pib='987654321',
            naziv='Test Firma 2',
            adresa='Test Adresa 2',
            broj='2',
            mesto='Beograd',
            postanski_broj='11000',
            maticni_broj='87654321',
            telefon='011234568',
            email='test2@firma.rs',
            dinarski_racuni=[{'racun': '987-654-321', 'banka': 'Test Banka 2'}]
        )
        db.session.add(firma)
        db.session.commit()

        # Create pausalac user
        pausalac = User(
            email='pausalac2@test.com',
            full_name='Test Pausalac 2',
            role='pausalac',
            firma_id=firma.id
        )
        pausalac.set_password('password123')
        db.session.add(pausalac)
        db.session.commit()

        # Login as pausalac
        login_user(pausalac)

        # Get firma_id
        result_firma_id = get_user_firma_id()

        # Pausalac should return their firma_id
        assert result_firma_id == firma.id

        # Cleanup
        logout_user()


def test_filter_by_firma_admin(app):
    """Test that filter_by_firma() does not filter for Admin user."""
    with app.test_request_context():
        # Create admin user
        admin = User(
            email='admin2@test.com',
            full_name='Test Admin 2',
            role='admin',
            firma_id=None
        )
        admin.set_password('password123')
        db.session.add(admin)
        db.session.commit()

        # Login as admin
        login_user(admin)

        # Create query
        query = Faktura.query
        filtered_query = filter_by_firma(query)

        # For admin, query should not have firma_id filter
        # Check that the SQL doesn't contain firma_id filter
        original_sql = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        filtered_sql = str(filtered_query.statement.compile(compile_kwargs={"literal_binds": True}))

        # Both should be the same (no filtering applied)
        assert original_sql == filtered_sql

        # Cleanup
        logout_user()


def test_filter_by_firma_pausalac(app):
    """Test that filter_by_firma() filters by firma_id for Pausalac user."""
    with app.test_request_context():
        # Create pausaln firma first
        firma = PausalnFirma(
            pib='111222333',
            naziv='Test Firma 3',
            adresa='Test Adresa 3',
            broj='3',
            mesto='Beograd',
            postanski_broj='11000',
            maticni_broj='11122233',
            telefon='011234569',
            email='test3@firma.rs',
            dinarski_racuni=[{'racun': '111-222-333', 'banka': 'Test Banka 3'}]
        )
        db.session.add(firma)
        db.session.commit()

        # Create pausalac user
        pausalac = User(
            email='pausalac3@test.com',
            full_name='Test Pausalac 3',
            role='pausalac',
            firma_id=firma.id
        )
        pausalac.set_password('password123')
        db.session.add(pausalac)
        db.session.commit()

        # Login as pausalac
        login_user(pausalac)

        # Create query
        query = Faktura.query
        filtered_query = filter_by_firma(query)

        # For pausalac, query should have firma_id filter
        filtered_sql = str(filtered_query.statement.compile(compile_kwargs={"literal_binds": True}))

        # Check that firma_id is in the WHERE clause
        assert 'firma_id' in filtered_sql.lower()
        assert str(firma.id) in filtered_sql

        # Cleanup
        logout_user()
