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
    from app.routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    # Register admin dashboard blueprint
    from app.routes.admin_dashboard import admin_dashboard_bp
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
    
    # Register fakture blueprint
    from app.routes.fakture import fakture_bp
    app.register_blueprint(fakture_bp)

    # Register memorandumi blueprint
    from app.routes.memorandumi import memorandumi_bp
    app.register_blueprint(memorandumi_bp)
    
    # Register KPO knjiga blueprint
    from app.routes.kpo import kpo_bp
    app.register_blueprint(kpo_bp)

    # TODO: Register other blueprints when they are created in future stories

    # Register before_request hook for session timeout
    @app.before_request
    def check_firm_context_timeout():
        """
        Check if admin firm context has timed out due to inactivity.

        If admin has selected a firma context and has been inactive for more than
        30 minutes, automatically clear the firm context and redirect to admin dashboard.

        This prevents admins from accidentally working in the wrong firma context
        after long periods of inactivity.
        """
        from flask import flash, redirect, url_for, request, session
        from flask_login import current_user
        from app.utils.query_helpers import get_admin_selected_firma_id, clear_admin_firm_context
        from datetime import datetime, timedelta, timezone

        # Only check for authenticated admin users with active firm context
        if not current_user.is_authenticated or not current_user.is_admin():
            return None

        admin_selected_firma_id = get_admin_selected_firma_id()
        if not admin_selected_firma_id:
            return None  # No firm context active, nothing to timeout

        # Get last activity time from session
        last_activity = session.get('last_activity_time')
        current_time = datetime.now(timezone.utc)

        # Initialize last_activity if not set
        if last_activity is None:
            session['last_activity_time'] = current_time
            return None

        # Ensure last_activity is timezone-aware (handle deserialized naive datetimes)
        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)

        # Check if session has timed out (30 minutes = 1800 seconds)
        timeout_threshold = timedelta(minutes=30)
        time_since_activity = current_time - last_activity

        if time_since_activity > timeout_threshold:
            # Session has timed out - clear firm context
            clear_admin_firm_context()
            session.pop('last_activity_time', None)
            flash('Sesija firme je istekla zbog neaktivnosti. Vraćeni ste u God Mode.', 'warning')

            # Redirect to admin dashboard (only for non-AJAX requests)
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if not is_ajax and request.endpoint != 'admin_dashboard.dashboard':
                return redirect(url_for('admin_dashboard.dashboard'))
        else:
            # Update last activity time
            session['last_activity_time'] = current_time

        return None

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

    # Register security headers middleware
    @app.after_request
    def set_security_headers(response):
        """
        Set security headers on all HTTP responses.

        Security headers prevent common web vulnerabilities:
        - X-Content-Type-Options: Prevents MIME type sniffing attacks
        - X-Frame-Options: Prevents clickjacking attacks
        - Strict-Transport-Security (HSTS): Forces HTTPS connections
        - Content-Security-Policy (CSP): Prevents XSS and data injection attacks

        Note: These headers are also configured in Nginx for production,
        but Flask middleware ensures they are set even in development/testing.

        Args:
            response: Flask response object

        Returns:
            Modified Flask response with security headers
        """
        # Prevent MIME type sniffing (force browser to respect Content-Type)
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Prevent clickjacking by disallowing iframe embedding
        response.headers['X-Frame-Options'] = 'DENY'

        # Force HTTPS for 1 year (only in production with HTTPS enabled)
        if app.config.get('SESSION_COOKIE_SECURE', False):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # Content Security Policy - restrict resource loading to trusted sources
        # - default-src 'self': Only load resources from same origin
        # - script-src: Allow scripts from same origin, inline scripts, and Bootstrap CDN
        # - style-src: Allow styles from same origin, inline styles, Bootstrap CDN, Font Awesome, and Google Fonts
        # - font-src: Allow fonts from same origin, Bootstrap CDN, Font Awesome, and Google Fonts
        # - img-src: Allow images from same origin and data: URIs (for inline images)
        # - connect-src: Allow AJAX requests to same origin only
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )

        return response

    # Register error handlers
    register_error_handlers(app)

    # Import models so they are registered with SQLAlchemy
    # This is necessary for Flask-Migrate to detect model changes
    with app.app_context():
        from app import models  # noqa: F401

    # Register CLI commands
    from app.cli import register_commands
    register_commands(app)

    return app


def register_error_handlers(app):
    """
    Register global error handlers for the application.

    Handles:
    - Custom API exceptions (ValidationError, NotFoundError, etc.)
    - Standard HTTP errors (404, 500)
    - Unexpected exceptions
    """
    from flask import jsonify, render_template, request
    from app.utils.exceptions import APIError, ValidationError, NotFoundError, UnauthorizedError, ServerError

    @app.errorhandler(APIError)
    def handle_api_error(error):
        """
        Handle custom API errors.

        Returns JSON for AJAX requests, HTML for regular requests.
        """
        app.logger.error(f'API Error: {error.message}', exc_info=True)

        # Check if request is AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  request.headers.get('Content-Type') == 'application/json' or \
                  request.path.startswith('/api/')

        if is_ajax:
            # Return JSON response for AJAX requests
            response = jsonify(error.to_dict())
            response.status_code = error.status_code
            return response
        else:
            # Return HTML error page for regular requests
            from flask import flash, redirect, url_for
            flash(error.message, 'danger')

            # Redirect back to referrer or home page
            referrer = request.referrer
            if referrer and referrer.startswith(request.url_root):
                return redirect(referrer)
            else:
                return redirect(url_for('dashboard.pausalac_dashboard'))

    @app.errorhandler(404)
    def handle_404(error):
        """
        Handle 404 Not Found errors.
        """
        app.logger.warning(f'404 Not Found: {request.url}')

        # Check if request is AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  request.path.startswith('/api/')

        if is_ajax:
            return jsonify({
                'error': 'Resurs nije pronađen',
                'status_code': 404
            }), 404
        else:
            # Return custom 404 page (or flash message and redirect)
            from flask import flash, redirect, url_for
            flash('Stranica koju tražite nije pronađena.', 'warning')
            return redirect(url_for('dashboard.pausalac_dashboard'))

    @app.errorhandler(403)
    def handle_403(error):
        """
        Handle 403 Forbidden errors.
        """
        app.logger.warning(f'403 Forbidden: {request.url}')

        # Check if request is AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  request.path.startswith('/api/')

        if is_ajax:
            return jsonify({
                'error': 'Nemate dozvolu za pristup ovom resursu',
                'status_code': 403
            }), 403
        else:
            from flask import flash, redirect, url_for
            flash('Nemate dozvolu za pristup ovoj stranici.', 'danger')
            return redirect(url_for('dashboard.pausalac_dashboard'))

    @app.errorhandler(429)
    def handle_rate_limit(error):
        """
        Handle 429 Too Many Requests (rate limit exceeded).

        Triggered when user exceeds rate limit (e.g., max 5 login attempts per 15 minutes).
        """
        app.logger.warning(f'429 Rate Limit Exceeded: {request.url} from IP: {request.remote_addr}')

        # Check if request is AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  request.path.startswith('/api/')

        if is_ajax:
            return jsonify({
                'error': 'Previše neuspelih pokušaja. Pokušajte ponovo za 15 minuta.',
                'status_code': 429
            }), 429
        else:
            from flask import flash, redirect, url_for
            flash('Previše neuspelih pokušaja. Pokušajte ponovo za 15 minuta.', 'warning')
            return redirect(url_for('auth.login'))

    @app.errorhandler(500)
    def handle_500(error):
        """
        Handle 500 Internal Server Error.
        """
        app.logger.error(f'500 Internal Server Error: {request.url}', exc_info=True)

        # Rollback database session in case of error
        db.session.rollback()

        # Check if request is AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  request.path.startswith('/api/')

        if is_ajax:
            return jsonify({
                'error': 'Greška na serveru. Molimo pokušajte ponovo.',
                'status_code': 500
            }), 500
        else:
            # Return custom 500 page (or flash message and redirect)
            from flask import flash, redirect, url_for
            flash('Greška na serveru. Molimo pokušajte ponovo.', 'danger')
            return redirect(url_for('dashboard.pausalac_dashboard'))

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """
        Handle unexpected exceptions.

        This is a catch-all for any unhandled exceptions.
        """
        app.logger.error(f'Unexpected error: {str(error)}', exc_info=True)

        # Rollback database session
        db.session.rollback()

        # Check if request is AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  request.path.startswith('/api/')

        if is_ajax:
            return jsonify({
                'error': 'Neočekivana greška. Molimo pokušajte ponovo.',
                'status_code': 500
            }), 500
        else:
            from flask import flash, redirect, url_for
            flash('Neočekivana greška. Molimo pokušajte ponovo.', 'danger')
            return redirect(url_for('dashboard.pausalac_dashboard'))
