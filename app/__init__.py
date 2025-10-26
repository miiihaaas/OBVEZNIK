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
from redis import Redis

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

    # Only initialize rate limiter if not disabled in config
    if app.config.get('RATELIMIT_ENABLED', True):
        limiter.init_app(app)
    else:
        app.logger.info("Rate limiting is disabled (testing mode)")

    # Initialize Redis
    try:
        redis_client = Redis.from_url(app.config['REDIS_URL'])
        redis_client.ping()  # Test connection
        app.extensions['redis'] = redis_client
        app.logger.info("Redis connected successfully")
    except Exception as e:
        app.logger.warning(f"Redis connection failed: {e}. Caching disabled.")
        app.extensions['redis'] = None

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

    # Register admin API blueprint (autocomplete, lazy load)
    from app.routes.admin_api import admin_api_bp
    app.register_blueprint(admin_api_bp)

    # Register API blueprint
    from app.routes.api import api_bp
    app.register_blueprint(api_bp)

    # Register komitenti blueprint
    from app.routes.komitenti import komitenti_bp
    app.register_blueprint(komitenti_bp)

    # Register artikli blueprint
    from app.routes.artikli import artikli_bp
    app.register_blueprint(artikli_bp)

    # TODO: Register other blueprints when they are created in future stories
    # from app.routes import fakture
    # app.register_blueprint(fakture.bp)

    # Register context processors
    @app.context_processor
    def inject_admin_firm_context():
        """
        Inject admin firm context into all templates.

        Provides pausaln_firme list and admin_selected_firma for navigation bar
        firm selector dropdown (admin only).

        Returns:
            dict: Context variables (pausaln_firme, admin_selected_firma)
        """
        from flask_login import current_user
        from app.models.pausaln_firma import PausalnFirma
        from app.utils.query_helpers import get_admin_selected_firma_id

        # Only inject for authenticated admin users
        if not current_user.is_authenticated or not current_user.is_admin():
            return dict(admin_selected_firma=None)

        # Get currently selected firma (if any)
        admin_selected_firma_id = get_admin_selected_firma_id()
        admin_selected_firma = None
        if admin_selected_firma_id:
            admin_selected_firma = db.session.get(PausalnFirma, admin_selected_firma_id)

        # Note: pausaln_firme is now loaded via AJAX for performance (lazy load)
        # See /api/admin/firme/search endpoint and base.html autocomplete JS
        return dict(
            admin_selected_firma=admin_selected_firma
        )

    # Import models so they are registered with SQLAlchemy
    # This is necessary for Flask-Migrate to detect model changes
    with app.app_context():
        from app import models  # noqa: F401

    # Register CLI commands
    from app.cli import register_commands
    register_commands(app)

    return app
