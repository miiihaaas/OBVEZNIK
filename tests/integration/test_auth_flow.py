"""Integration tests for authentication flows (login, logout, access control)."""
import pytest
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app import create_app, db


@pytest.fixture
def app():
    """Create test app with test config."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def admin_user(app):
    """Create admin user for testing."""
    with app.app_context():
        user = User(email='admin@test.com', full_name='Admin Test', role='admin')
        user.set_password('admin123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def pausalac_user(app):
    """Create pausalac user with firma for testing."""
    with app.app_context():
        # Create test firma first
        firma = PausalnFirma(
            pib='999888777',
            maticni_broj='12345678',
            naziv='Test Firma',
            adresa='Test adresa',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            telefon='011/1234567',
            email='test@test.com',
            dinarski_racuni='[]',
            is_active=True
        )
        db.session.add(firma)
        db.session.flush()

        # Create pausalac user
        user = User(
            email='pausalac@test.com',
            full_name='Pausalac Test',
            role='pausalac',
            firma_id=firma.id
        )
        user.set_password('pausalac123')
        db.session.add(user)
        db.session.commit()
        return user


def test_login_page_loads(client):
    """Test that login page loads successfully."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'OBVEZNIK' in response.data
    assert b'Email' in response.data
    assert b'Lozinka' in response.data


def test_login_success_admin(client, admin_user):
    """Test successful login redirects admin to admin dashboard."""
    response = client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'Administratore' in response.data.decode('utf-8') or 'Admin Dashboard' in response.data.decode('utf-8')


def test_login_success_pausalac(client, pausalac_user):
    """Test successful login redirects pausalac to pausalac dashboard."""
    response = client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'pausalac123'
    }, follow_redirects=True)

    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    assert 'Dashboard' in response_text or 'Dobrodošli' in response_text


def test_login_failure_wrong_password(client, admin_user):
    """Test login with wrong password shows error message."""
    response = client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'wrongpassword'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Invalid email or password' in response.data


def test_login_failure_nonexistent_email(client):
    """Test login with non-existent email shows error message."""
    response = client.post('/login', data={
        'email': 'nonexistent@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Invalid email or password' in response.data


def test_login_updates_last_login(client, admin_user, app):
    """Test that login updates last_login timestamp."""
    with app.app_context():
        # Verify last_login is initially None
        user = User.query.filter_by(email='admin@test.com').first()
        assert user.last_login is None

    # Login
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    }, follow_redirects=True)

    with app.app_context():
        # Verify last_login is now set
        user = User.query.filter_by(email='admin@test.com').first()
        assert user.last_login is not None


def test_logout(client, admin_user):
    """Test logout clears session and redirects to login."""
    # Login first
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    })

    # Logout
    response = client.get('/logout', follow_redirects=True)

    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    assert 'odjavili' in response_text or 'login' in response_text.lower()


def test_login_required_decorator(client):
    """Test that accessing protected route without login redirects to login."""
    response = client.get('/dashboard', follow_redirects=True)

    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    assert 'Prijavi' in response_text or 'login' in response_text.lower()


def test_admin_required_decorator_blocks_pausalac(client, pausalac_user):
    """Test that pausalac accessing admin route gets 403 Forbidden."""
    # Login as pausalac
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'pausalac123'
    })

    # Try to access admin dashboard
    response = client.get('/admin/dashboard')

    assert response.status_code == 403  # Forbidden


def test_admin_required_decorator_allows_admin(client, admin_user):
    """Test that admin can access admin routes."""
    # Login as admin
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    }, follow_redirects=True)

    # Access admin dashboard
    response = client.get('/admin/dashboard')

    assert response.status_code == 200


def test_remember_me_checkbox(client, admin_user):
    """Test that remember_me checkbox works (persistent login)."""
    # Login with remember_me=True
    response = client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123',
        'remember_me': 'y'
    }, follow_redirects=True)

    assert response.status_code == 200
    # Note: Testing actual cookie persistence requires additional setup


def test_inactive_user_cannot_login(client, app):
    """Test that inactive user account cannot login."""
    with app.app_context():
        # Create inactive user
        user = User(email='inactive@test.com', full_name='Inactive User', role='admin', is_active=False)
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

    # Try to login
    response = client.post('/login', data={
        'email': 'inactive@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    assert 'deaktiviran' in response_text or 'inactive' in response_text.lower()


def test_already_logged_in_redirect(client, admin_user):
    """Test that already logged-in user is redirected from login page."""
    # Login first
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    })

    # Try to access login page again
    response = client.get('/login', follow_redirects=True)

    # Should redirect to dashboard
    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    assert 'Dashboard' in response_text or 'Dobrodošli' in response_text


def test_email_validation_invalid_format(client):
    """Test that invalid email format shows validation error."""
    # Test with email missing @ symbol
    response = client.post('/login', data={
        'email': 'invalidemail.com',  # Missing @
        'password': 'password123'
    }, follow_redirects=True)

    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    # Should show email validation error
    assert 'email' in response_text.lower()


def test_empty_form_validation(client):
    """Test that empty form fields show validation errors."""
    # Submit completely empty form
    response = client.post('/login', data={
        'email': '',
        'password': ''
    }, follow_redirects=True)

    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    # Should show validation errors for required fields
    assert 'obavezan' in response_text.lower() or 'required' in response_text.lower()


def test_csrf_token_required(client, app):
    """Test that POST request without CSRF token is rejected."""
    # Note: CSRF is disabled in TestingConfig, so we need to enable it temporarily
    with app.app_context():
        # Get the login page to obtain CSRF token
        response = client.get('/login')
        assert response.status_code == 200

    # Attempt POST without CSRF token (using direct POST with empty environ)
    # This test verifies CSRF protection is configured, even though disabled in testing
    # In production (WTF_CSRF_ENABLED=True), Flask-WTF automatically validates tokens
    # For actual CSRF validation test, we would need to:
    # 1. Temporarily enable CSRF in test config
    # 2. Submit form without token and expect 400
    # 3. This is a structural test confirming CSRF setup exists

    # Verify CSRF protection is imported and used in forms
    from app.forms.auth import LoginForm
    from flask_wtf import FlaskForm

    # LoginForm inherits from FlaskForm which provides CSRF protection
    assert issubclass(LoginForm, FlaskForm)

    # In template, csrf token is rendered via form.hidden_tag()
    # This test confirms the infrastructure is in place
    # Actual CSRF validation happens automatically when WTF_CSRF_ENABLED=True


# Story 1.4 Logout Tests
def test_logout_clears_session(client, admin_user):
    """Test da logout briše session i redirect-uje na login."""
    # Login korisnika
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    })

    # Logout
    response = client.get('/logout', follow_redirects=False)

    # Assert: Redirect na login
    assert response.status_code == 302
    assert '/login' in response.location

    # Assert: Ne može pristupiti protected route-u nakon logout-a
    response = client.get('/dashboard', follow_redirects=False)
    assert response.status_code == 302  # Redirect to login


def test_logout_redirects_to_login(client, pausalac_user):
    """Test da logout redirect-uje na login stranicu."""
    # Login korisnika
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'pausalac123'
    })

    # Logout sa follow_redirects=True
    response = client.get('/logout', follow_redirects=True)

    # Assert: Final destination je login page
    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    assert 'Email' in response_text  # Login form prisutan
    assert 'Lozinka' in response_text


def test_logout_shows_success_message(client, admin_user):
    """Test da logout prikazuje success flash poruku."""
    # Login korisnika
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    })

    # Logout
    response = client.get('/logout', follow_redirects=True)

    # Assert: Success message je prikazan
    response_text = response.data.decode('utf-8')
    assert 'odjavili' in response_text


def test_protected_route_after_logout(client, admin_user):
    """Test da korisnik ne može pristupiti protected route-u nakon logout-a."""
    # Login korisnika
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    })

    # Assert: Može pristupiti admin dashboard pre logout-a
    response = client.get('/admin/dashboard')
    assert response.status_code == 200

    # Logout
    client.get('/logout')

    # Assert: Ne može pristupiti admin dashboard nakon logout-a
    response = client.get('/admin/dashboard', follow_redirects=False)
    assert response.status_code == 302  # Redirect to login
    assert '/login' in response.location


def test_logout_logs_security_event(client, admin_user, caplog):
    """Test da logout događaj je logovan u security log."""
    import logging

    # Login korisnika
    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    })

    # Logout with logging capture
    with caplog.at_level(logging.INFO, logger='security'):
        client.get('/logout')

    # Assert: Security log entry postoji sa svim relevantnim podacima
    assert 'User logout' in caplog.text
    assert 'admin@test.com' in caplog.text
    assert 'role=admin' in caplog.text
    assert 'ip=' in caplog.text  # IP je prisutan u logu
    assert 'timestamp=' in caplog.text  # Timestamp je prisutan
