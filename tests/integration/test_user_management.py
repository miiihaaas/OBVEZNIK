"""Integration tests for User Management (Admin CRUD)."""
import pytest
from flask import url_for
from app import create_app, db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma


@pytest.fixture
def app():
    """Create application for testing."""
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
    admin = User(
        email='admin@test.com',
        full_name='Test Admin',
        role='admin'
    )
    admin.set_password('password123')
    db.session.add(admin)
    db.session.commit()
    return admin


@pytest.fixture
def pausalac_user(app):
    """Create pausalac user for testing."""
    pausalac = User(
        email='pausalac@test.com',
        full_name='Test Pausalac',
        role='pausalac'
    )
    pausalac.set_password('password123')
    db.session.add(pausalac)
    db.session.commit()
    return pausalac


@pytest.fixture
def firma(app):
    """Create test PausalnFirma."""
    firma = PausalnFirma(
        pib='123456789',
        maticni_broj='12345678',
        naziv='Test Firma',
        adresa='Test Adresa',
        broj='1',
        postanski_broj='11000',
        mesto='Beograd',
        telefon='011111111',
        email='firma@test.com',
        dinarski_racuni=[{'banka': 'Test Banka', 'broj': '123-456789-00'}]
    )
    db.session.add(firma)
    db.session.commit()
    return firma


def login(client, email, password):
    """Helper function to login user."""
    return client.post('/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)


def test_admin_can_view_users_list(client, app, admin_user):
    """Test that admin can view users list."""
    login(client, 'admin@test.com', 'password123')

    response = client.get('/admin/users')

    assert response.status_code == 200
    assert Korisnici' in response.data.decode("utf-8")
    assert admin@test.com' in response.data.decode("utf-8")


def test_pausalac_cannot_view_users_list(client, app, pausalac_user):
    """Test that pausalac cannot view users list."""
    login(client, 'pausalac@test.com', 'password123')

    response = client.get('/admin/users', follow_redirects=False)

    assert response.status_code == 403


def test_unauthenticated_user_redirected_to_login(client, app):
    """Test that unauthenticated user is redirected to login."""
    response = client.get('/admin/users', follow_redirects=False)

    assert response.status_code == 302
    assert '/login' in response.location


def test_admin_can_view_user_create_form(client, app, admin_user):
    """Test that admin can view user creation form."""
    login(client, 'admin@test.com', 'password123')

    response = client.get('/admin/users/novi')

    assert response.status_code == 200
    assert Kreiraj Korisnika' in response.data.decode("utf-8")
    assert Ime i Prezime' in response.data.decode("utf-8")
    assert Email' in response.data.decode("utf-8")


def test_admin_can_create_new_admin_user(client, app, admin_user):
    """Test that admin can create new admin user."""
    login(client, 'admin@test.com', 'password123')

    response = client.post('/admin/users/novi', data={
        'full_name': 'New Admin',
        'email': 'newadmin@test.com',
        'password': 'newpassword123',
        'role': 'admin',
        'firma_id': 0
    }, follow_redirects=True)

    assert response.status_code == 200
    assert uspešno kreiran' in response.data.decode("utf-8")

    # Verify user was created in database
    new_user = User.query.filter_by(email='newadmin@test.com').first()
    assert new_user is not None
    assert new_user.full_name == 'New Admin'
    assert new_user.role == 'admin'
    assert new_user.firma_id is None


def test_admin_can_create_new_pausalac_user(client, app, admin_user, firma):
    """Test that admin can create new pausalac user with firma_id."""
    login(client, 'admin@test.com', 'password123')

    response = client.post('/admin/users/novi', data={
        'full_name': 'New Pausalac',
        'email': 'newpausalac@test.com',
        'password': 'newpassword123',
        'role': 'pausalac',
        'firma_id': firma.id
    }, follow_redirects=True)

    assert response.status_code == 200
    assert uspešno kreiran' in response.data.decode("utf-8")

    # Verify user was created in database
    new_user = User.query.filter_by(email='newpausalac@test.com').first()
    assert new_user is not None
    assert new_user.full_name == 'New Pausalac'
    assert new_user.role == 'pausalac'
    assert new_user.firma_id == firma.id


def test_email_uniqueness_validation(client, app, admin_user):
    """Test that backend validates email uniqueness."""
    login(client, 'admin@test.com', 'password123')

    # Try to create user with existing email
    response = client.post('/admin/users/novi', data={
        'full_name': 'Duplicate Admin',
        'email': 'admin@test.com',  # Duplicate email
        'password': 'password123',
        'role': 'admin',
        'firma_id': 0
    }, follow_redirects=True)

    assert response.status_code == 200
    assert Email je već registrovan' in response.data.decode("utf-8")


def test_firma_required_for_pausalac(client, app, admin_user):
    """Test that backend validates firma_id is required for pausalac."""
    login(client, 'admin@test.com', 'password123')

    response = client.post('/admin/users/novi', data={
        'full_name': 'Test Pausalac',
        'email': 'pausalac2@test.com',
        'password': 'password123',
        'role': 'pausalac',
        'firma_id': 0  # Missing firma_id
    }, follow_redirects=True)

    assert response.status_code == 200
    assert Morate izabrati paušalnu firmu' in response.data.decode("utf-8")


def test_admin_can_view_user_edit_form(client, app, admin_user, pausalac_user):
    """Test that admin can view user edit form."""
    login(client, 'admin@test.com', 'password123')

    response = client.get(f'/admin/users/{pausalac_user.id}/izmeni')

    assert response.status_code == 200
    assert Izmeni Korisnika' in response.data.decode("utf-8")
    assert pausalac@test.com' in response.data.decode("utf-8")


def test_admin_can_edit_user(client, app, admin_user, pausalac_user, firma):
    """Test that admin can edit existing user."""
    login(client, 'admin@test.com', 'password123')

    response = client.post(f'/admin/users/{pausalac_user.id}/izmeni', data={
        'full_name': 'Updated Pausalac',
        'email': 'updated@test.com',
        'password': '',  # Don't change password
        'role': 'pausalac',
        'firma_id': firma.id
    }, follow_redirects=True)

    assert response.status_code == 200
    assert uspešno ažuriran' in response.data.decode("utf-8")

    # Verify user was updated in database
    updated_user = User.query.get(pausalac_user.id)
    assert updated_user.full_name == 'Updated Pausalac'
    assert updated_user.email == 'updated@test.com'


def test_admin_can_edit_user_without_changing_password(client, app, admin_user, pausalac_user):
    """Test that admin can edit user without changing password."""
    login(client, 'admin@test.com', 'password123')

    original_password_hash = pausalac_user.password_hash

    response = client.post(f'/admin/users/{pausalac_user.id}/izmeni', data={
        'full_name': 'Updated Name',
        'email': 'pausalac@test.com',
        'password': '',  # Empty password
        'role': 'pausalac',
        'firma_id': 0
    }, follow_redirects=True)

    assert response.status_code == 200

    # Verify password hash didn't change
    updated_user = User.query.get(pausalac_user.id)
    assert updated_user.password_hash == original_password_hash


def test_admin_can_edit_user_with_new_password(client, app, admin_user, pausalac_user):
    """Test that admin can edit user with new password."""
    login(client, 'admin@test.com', 'password123')

    original_password_hash = pausalac_user.password_hash

    response = client.post(f'/admin/users/{pausalac_user.id}/izmeni', data={
        'full_name': 'Test Pausalac',
        'email': 'pausalac@test.com',
        'password': 'newpassword456',  # New password
        'role': 'pausalac',
        'firma_id': 0
    }, follow_redirects=True)

    assert response.status_code == 200

    # Verify password hash changed
    updated_user = User.query.get(pausalac_user.id)
    assert updated_user.password_hash != original_password_hash
    assert updated_user.check_password('newpassword456') is True


def test_admin_can_delete_user(client, app, admin_user, pausalac_user):
    """Test that admin can delete user."""
    login(client, 'admin@test.com', 'password123')

    user_id = pausalac_user.id

    response = client.post(f'/admin/users/{user_id}/obrisi', follow_redirects=True)

    assert response.status_code == 200
    assert uspešno obrisan' in response.data.decode("utf-8")

    # Verify user was deleted from database
    deleted_user = User.query.get(user_id)
    assert deleted_user is None


def test_admin_cannot_delete_self(client, app, admin_user):
    """Test that admin cannot delete their own account."""
    login(client, 'admin@test.com', 'password123')

    response = client.post(f'/admin/users/{admin_user.id}/obrisi', follow_redirects=True)

    assert response.status_code == 200
    assert Ne možete obrisati svoj nalog' in response.data.decode("utf-8")

    # Verify admin still exists
    still_exists = User.query.get(admin_user.id)
    assert still_exists is not None


def test_user_creation_logged_in_security_log(client, app, admin_user, caplog):
    """Test that user creation is logged in security log."""
    import logging
    caplog.set_level(logging.INFO, logger='security')

    login(client, 'admin@test.com', 'password123')

    client.post('/admin/users/novi', data={
        'full_name': 'New User',
        'email': 'newuser@test.com',
        'password': 'password123',
        'role': 'admin',
        'firma_id': 0
    }, follow_redirects=True)

    # Check security log
    assert any('User created' in record.message for record in caplog.records)
    assert any('newuser@test.com' in record.message for record in caplog.records)


def test_user_update_logged_in_security_log(client, app, admin_user, pausalac_user, caplog):
    """Test that user update is logged in security log."""
    import logging
    caplog.set_level(logging.INFO, logger='security')

    login(client, 'admin@test.com', 'password123')

    client.post(f'/admin/users/{pausalac_user.id}/izmeni', data={
        'full_name': 'Updated User',
        'email': 'pausalac@test.com',
        'password': '',
        'role': 'pausalac',
        'firma_id': 0
    }, follow_redirects=True)

    # Check security log
    assert any('User updated' in record.message for record in caplog.records)


def test_user_deletion_logged_in_security_log(client, app, admin_user, pausalac_user, caplog):
    """Test that user deletion is logged in security log."""
    import logging
    caplog.set_level(logging.INFO, logger='security')

    login(client, 'admin@test.com', 'password123')

    client.post(f'/admin/users/{pausalac_user.id}/obrisi', follow_redirects=True)

    # Check security log
    assert any('User deleted' in record.message for record in caplog.records)
    assert any('pausalac@test.com' in record.message for record in caplog.records)
