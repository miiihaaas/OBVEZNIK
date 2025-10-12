"""Unit tests for User Management forms."""
import pytest
from app.forms.user import UserCreateForm, UserEditForm
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app import create_app, db


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
def firma(app):
    """Create a test PausalnFirma."""
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


def test_user_create_form_valid_admin_data(app):
    """Test that UserCreateForm validates valid admin data."""
    with app.test_request_context():
        form = UserCreateForm(
            full_name='Test Admin',
            email='admin@test.com',
            password='password123',
            role='admin',
            firma_id=0
        )
        form.firma_id.choices = [(0, 'Izaberite firmu...')]

        assert form.validate() is True


def test_user_create_form_valid_pausalac_data(app, firma):
    """Test that UserCreateForm validates valid pausalac data with firma_id."""
    with app.test_request_context():
        form = UserCreateForm(
            full_name='Test Pausalac',
            email='pausalac@test.com',
            password='password123',
            role='pausalac',
            firma_id=firma.id
        )
        form.firma_id.choices = [(0, 'Izaberite firmu...'), (firma.id, firma.naziv)]

        assert form.validate() is True


def test_user_create_form_invalid_email_format(app):
    """Test that UserCreateForm rejects invalid email format."""
    with app.test_request_context():
        form = UserCreateForm(
            full_name='Test User',
            email='invalid-email',
            password='password123',
            role='admin',
            firma_id=0
        )
        form.firma_id.choices = [(0, 'Izaberite firmu...')]

        assert form.validate() is False
        assert 'email' in form.errors


def test_user_create_form_duplicate_email(app):
    """Test that UserCreateForm rejects duplicate email."""
    # Create existing user
    existing_user = User(
        email='existing@test.com',
        full_name='Existing User',
        role='admin'
    )
    existing_user.set_password('password123')
    db.session.add(existing_user)
    db.session.commit()

    with app.test_request_context():
        form = UserCreateForm(
            full_name='New User',
            email='existing@test.com',  # Duplicate email
            password='password123',
            role='admin',
            firma_id=0
        )
        form.firma_id.choices = [(0, 'Izaberite firmu...')]

        assert form.validate() is False
        assert 'email' in form.errors
        assert 'Email je već registrovan.' in form.errors['email']


def test_user_create_form_pausalac_requires_firma(app):
    """Test that UserCreateForm requires firma_id for pausalac role."""
    from werkzeug.datastructures import MultiDict

    with app.test_request_context():
        form_data = MultiDict([
            ('full_name', 'Test Pausalac'),
            ('email', 'pausalac_unique@test.com'),
            ('password', 'password123'),
            ('role', 'pausalac'),
            ('firma_id', '0')  # Missing firma_id
        ])

        form = UserCreateForm(formdata=form_data)
        form.firma_id.choices = [(0, 'Izaberite firmu...')]

        assert form.validate() is False
        assert 'firma_id' in form.errors
        assert 'Morate izabrati paušalnu firmu' in form.errors['firma_id'][0]


def test_user_create_form_missing_required_fields(app):
    """Test that UserCreateForm rejects missing required fields."""
    with app.test_request_context():
        form = UserCreateForm(
            full_name='',
            email='',
            password='',
            role='admin',
            firma_id=0
        )
        form.firma_id.choices = [(0, 'Izaberite firmu...')]

        assert form.validate() is False
        assert 'full_name' in form.errors
        assert 'email' in form.errors
        assert 'password' in form.errors


def test_user_edit_form_allows_same_email(app):
    """Test that UserEditForm allows existing email for current user."""
    # Create existing user
    existing_user = User(
        email='existing@test.com',
        full_name='Existing User',
        role='admin'
    )
    existing_user.set_password('password123')
    db.session.add(existing_user)
    db.session.commit()

    with app.test_request_context():
        form = UserEditForm(
            original_email='existing@test.com',
            full_name='Existing User',
            email='existing@test.com',  # Same email
            password='',  # Optional for edit
            role='admin',
            firma_id=0
        )
        form.firma_id.choices = [(0, 'Izaberite firmu...')]

        assert form.validate() is True


def test_user_edit_form_rejects_duplicate_email(app):
    """Test that UserEditForm rejects email that belongs to another user."""
    # Create two users
    user1 = User(email='user1@test.com', full_name='User 1', role='admin')
    user1.set_password('password123')

    user2 = User(email='user2@test.com', full_name='User 2', role='admin')
    user2.set_password('password123')

    db.session.add_all([user1, user2])
    db.session.commit()

    with app.test_request_context():
        # Try to change user1's email to user2's email
        form = UserEditForm(
            original_email='user1@test.com',
            full_name='User 1',
            email='user2@test.com',  # Duplicate email from another user
            password='',
            role='admin',
            firma_id=0
        )
        form.firma_id.choices = [(0, 'Izaberite firmu...')]

        assert form.validate() is False
        assert 'email' in form.errors
        assert 'Email je već registrovan.' in form.errors['email']


def test_user_edit_form_optional_password(app):
    """Test that UserEditForm allows empty password field."""
    with app.test_request_context():
        form = UserEditForm(
            original_email='test@test.com',
            full_name='Test User',
            email='test@test.com',
            password='',  # Empty password should be valid
            role='admin',
            firma_id=0
        )
        form.firma_id.choices = [(0, 'Izaberite firmu...')]

        assert form.validate() is True
