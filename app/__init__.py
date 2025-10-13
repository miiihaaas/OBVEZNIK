"""
Flask application factory.
Creates and configures the Flask application with all extensions.
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import config

# Initialize extensions (but don't bind to app yet)
db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
csrf = CSRFProtect()
mail = Mail()
migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # Use Redis in production via config
)


def create_app(config_name='development'):
    """
    Application factory function.

    Args:
        config_name: Configuration to use ('development', 'production', 'testing')

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # Configure logging
    config[config_name].configure_logging(app)

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Molimo prijavite se da pristupite ovoj stranici.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        """
        Flask-Login user_loader callback.
        Loads user by ID from database for session management.

        Args:
            user_id: String representation of user ID

        Returns:
            User object or None if not found
        """
        from app.models.user import User
        return User.query.get(int(user_id))

    # Register blueprints
    # Health check endpoint (simple route, not a blueprint)
    @app.route('/health')
    def health():
        """Health check endpoint for monitoring."""
        return {'status': 'ok'}, 200

    # Register auth blueprint
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    # Register dashboard blueprints
    from app.routes.dashboard import dashboard_bp, admin_dashboard_bp
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_dashboard_bp)

    # Register admin user management blueprint
    from app.routes.admin import admin_bp
    app.register_blueprint(admin_bp)

    # TODO: Register other blueprints when they are created in future stories
    # from app.routes import fakture, komitenti, artikli
    # app.register_blueprint(fakture.bp)
    # app.register_blueprint(komitenti.bp)
    # app.register_blueprint(artikli.bp)

    # Import models so they are registered with SQLAlchemy
    # This is necessary for Flask-Migrate to detect model changes
    with app.app_context():
        from app import models  # noqa: F401

    # Register CLI commands
    from app.cli import register_commands
    register_commands(app)

    return app
