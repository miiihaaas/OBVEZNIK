"""
Unit tests for Flask app factory and configuration.
"""
import pytest
from flask import Flask
from app import create_app, db, login_manager, bcrypt, csrf, mail
from config import config


class TestAppFactory:
    """Test suite for the Flask application factory."""

    def test_create_app_returns_flask_instance(self):
        """Test that create_app returns a Flask application instance."""
        app = create_app('testing')
        assert isinstance(app, Flask)

    def test_create_app_with_development_config(self):
        """Test app creation with development configuration."""
        app = create_app('development')
        assert app.config['DEBUG'] is True
        assert app.config['TESTING'] is False

    def test_create_app_with_production_config(self):
        """Test app creation with production configuration."""
        app = create_app('production')
        assert app.config['DEBUG'] is False
        assert app.config['TESTING'] is False

    def test_create_app_with_testing_config(self):
        """Test app creation with testing configuration."""
        app = create_app('testing')
        assert app.config['TESTING'] is True
        assert app.config['DEBUG'] is True
        assert app.config['WTF_CSRF_ENABLED'] is False

    def test_create_app_default_config(self):
        """Test that create_app defaults to development config."""
        app = create_app()
        assert app.config['DEBUG'] is True


class TestConfiguration:
    """Test suite for application configuration."""

    def test_secret_key_is_configured(self, app):
        """Test that SECRET_KEY is configured."""
        assert app.config['SECRET_KEY'] is not None
        assert len(app.config['SECRET_KEY']) > 0

    def test_database_uri_is_configured(self, app):
        """Test that SQLALCHEMY_DATABASE_URI is configured."""
        assert app.config['SQLALCHEMY_DATABASE_URI'] is not None
        assert 'mysql+pymysql' in app.config['SQLALCHEMY_DATABASE_URI']

    def test_sqlalchemy_track_modifications_disabled(self, app):
        """Test that SQLALCHEMY_TRACK_MODIFICATIONS is disabled."""
        assert app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] is False

    def test_bcrypt_log_rounds_configured(self, app):
        """Test that BCRYPT_LOG_ROUNDS is configured correctly."""
        # In testing mode, should be 4 for faster tests
        assert app.config['BCRYPT_LOG_ROUNDS'] == 4

    def test_sqlalchemy_engine_options_configured(self, app):
        """Test that SQLAlchemy engine options are configured."""
        engine_options = app.config['SQLALCHEMY_ENGINE_OPTIONS']
        assert engine_options['pool_pre_ping'] is True
        assert engine_options['pool_recycle'] == 3600


class TestExtensions:
    """Test suite for Flask extensions initialization."""

    def test_database_extension_initialized(self, app):
        """Test that SQLAlchemy database extension is initialized."""
        assert db is not None
        # Check that db is bound to the app
        with app.app_context():
            assert db.engine is not None

    def test_login_manager_initialized(self, app):
        """Test that Flask-Login extension is initialized."""
        assert login_manager is not None
        assert login_manager.login_view == 'auth.login'
        assert login_manager.login_message == 'Molimo prijavite se da pristupite ovoj stranici.'

    def test_bcrypt_initialized(self, app):
        """Test that Flask-Bcrypt extension is initialized."""
        assert bcrypt is not None

    def test_csrf_initialized(self, app):
        """Test that CSRF protection is initialized."""
        assert csrf is not None

    def test_mail_initialized(self, app):
        """Test that Flask-Mail extension is initialized."""
        assert mail is not None


class TestHealthEndpoint:
    """Test suite for the /health endpoint."""

    def test_health_endpoint_exists(self, client):
        """Test that /health endpoint exists."""
        response = client.get('/health')
        assert response.status_code == 200

    def test_health_endpoint_returns_json(self, client):
        """Test that /health endpoint returns JSON."""
        response = client.get('/health')
        assert response.content_type == 'application/json'

    def test_health_endpoint_returns_ok_status(self, client):
        """Test that /health endpoint returns correct status."""
        response = client.get('/health')
        data = response.get_json()
        assert data == {'status': 'ok'}

    def test_health_endpoint_accepts_only_get(self, client):
        """Test that /health endpoint only accepts GET requests."""
        response = client.post('/health')
        assert response.status_code == 405  # Method Not Allowed


class TestAppContext:
    """Test suite for Flask application context."""

    def test_app_context_available(self, app):
        """Test that application context is available."""
        with app.app_context():
            from flask import current_app
            assert current_app is not None
            assert current_app == app

    def test_database_connection_in_context(self, app):
        """Test that database connection works within app context."""
        with app.app_context():
            # This should not raise an exception
            assert db.engine is not None
