"""Unit tests for authentication service (password hashing)."""
import pytest
from app.models.user import User
from app import create_app, db
from datetime import datetime, timezone


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


def test_set_password(app):
    """Test password is hashed correctly."""
    with app.app_context():
        user = User(email='test@example.com', full_name='Test User', role='admin')
        user.set_password('password123')

        # Verify hash is created
        assert user.password_hash is not None
        # Verify hash is not plain text
        assert user.password_hash != 'password123'
        # Verify hash starts with bcrypt prefix
        assert user.password_hash.startswith('$2b$')


def test_check_password_correct(app):
    """Test password verification with correct password."""
    with app.app_context():
        user = User(email='test@example.com', full_name='Test User', role='admin')
        user.set_password('password123')

        # Correct password should return True
        assert user.check_password('password123') == True


def test_check_password_incorrect(app):
    """Test password verification with incorrect password."""
    with app.app_context():
        user = User(email='test@example.com', full_name='Test User', role='admin')
        user.set_password('password123')

        # Incorrect password should return False
        assert user.check_password('wrongpassword') == False
        assert user.check_password('Password123') == False  # Case sensitive
        assert user.check_password('') == False  # Empty password


def test_password_hashing_is_secure(app):
    """Test that same password generates different hashes (bcrypt salt)."""
    with app.app_context():
        user1 = User(email='user1@example.com', full_name='User 1', role='admin')
        user2 = User(email='user2@example.com', full_name='User 2', role='admin')

        user1.set_password('password123')
        user2.set_password('password123')

        # Same password should generate different hashes due to random salt
        assert user1.password_hash != user2.password_hash


def test_update_last_login(app):
    """Test last_login timestamp is updated."""
    with app.app_context():
        user = User(email='test@example.com', full_name='Test User', role='admin')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        # Initially last_login should be None
        assert user.last_login is None

        # Update last_login
        user.update_last_login()

        # Refresh user from DB to get stored value
        db.session.refresh(user)

        # Verify last_login is set and is recent (within last minute)
        assert user.last_login is not None
        now = datetime.now(timezone.utc)
        # SQLAlchemy stores datetime as naive, so convert to UTC for comparison
        last_login_utc = user.last_login.replace(tzinfo=timezone.utc)
        time_diff = (now - last_login_utc).total_seconds()
        assert time_diff < 60  # Should be less than 60 seconds ago


def test_password_hash_bcrypt_cost_factor(app):
    """Test that bcrypt uses cost factor 12 (2^12 rounds)."""
    with app.app_context():
        user = User(email='test@example.com', full_name='Test User', role='admin')
        user.set_password('password123')

        # Bcrypt hash format: $2b$rounds$salt+hash
        # Extract rounds from hash (characters 4-6)
        hash_parts = user.password_hash.split('$')
        rounds = int(hash_parts[2])

        # Verify cost factor is 12
        assert rounds == 12
