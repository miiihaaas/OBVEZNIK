"""
Flask application configuration.
Defines environment-based configuration classes.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration with common settings."""

    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Session security
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to cookies
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    SESSION_COOKIE_SECURE = False  # Set to True in ProductionConfig (requires HTTPS)

    # CSRF protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get('CSRF_SECRET_KEY') or SECRET_KEY

    @classmethod
    def init_app(cls, app):
        """Initialize application with configuration-specific settings."""
        pass

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://root:password@localhost:3306/obveznik'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Verify connections before using
        'pool_recycle': 3600,   # Recycle connections after 1 hour
    }

    # Bcrypt
    BCRYPT_LOG_ROUNDS = 12  # Cost factor for password hashing

    # Mail (SendGrid SMTP)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.sendgrid.net'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'apikey'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or ''
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@obveznik.com'

    # Redis
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'

    # Celery (using old format with CELERY_ prefix for compatibility)
    CELERY_BROKER_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

    # NBS Komitent API
    NBS_USERNAME = os.environ.get('NBS_USERNAME') or ''
    NBS_PASSWORD = os.environ.get('NBS_PASSWORD') or ''
    NBS_LICENCE_ID = os.environ.get('NBS_LICENCE_ID') or ''

    # File Storage
    STORAGE_PATH = os.path.join(os.path.dirname(__file__), 'storage', 'fakture')

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    SECURITY_LOG_FILE = os.path.join(os.path.dirname(__file__), 'logs', 'security.log')

    @classmethod
    def configure_logging(cls, app):
        """Configure application logging including security logger."""
        import logging
        from logging.handlers import RotatingFileHandler
        import os

        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)

        # Configure security logger
        security_logger = logging.getLogger('security')
        security_logger.setLevel(logging.INFO)

        # File handler for security logs
        security_handler = RotatingFileHandler(
            cls.SECURITY_LOG_FILE,
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        security_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s'
        ))
        security_logger.addHandler(security_handler)

        # Also log to console in development
        if app.config.get('DEBUG'):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '[%(asctime)s] %(levelname)s: %(message)s'
            ))
            security_logger.addHandler(console_handler)


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    TESTING = False

    # Production session security (HTTPS required)
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_SAMESITE = 'Strict'  # Stricter CSRF protection

    # In production, enforce environment variables
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # Ensure critical environment variables are set
        assert os.environ.get('SECRET_KEY'), 'SECRET_KEY must be set in production'
        assert os.environ.get('DATABASE_URL'), 'DATABASE_URL must be set in production'


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    DEBUG = True

    # Use separate test database
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'mysql+pymysql://root:password@localhost:3306/obveznik_test'

    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False

    # Faster password hashing for tests
    BCRYPT_LOG_ROUNDS = 4

    # Disable rate limiting for tests
    RATELIMIT_ENABLED = False

    # Optimized connection pooling for tests (module-scoped fixtures)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 2,         # Small pool since app is module-scoped
        'max_overflow': 0,      # No overflow connections
        'pool_recycle': 3600,   # Recycle connections after 1 hour
        'pool_pre_ping': True,  # Verify connections before using
    }


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
