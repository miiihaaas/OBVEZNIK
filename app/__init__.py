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

from config import config

# Initialize extensions (but don't bind to app yet)
db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
csrf = CSRFProtect()
mail = Mail()
migrate = Migrate()


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

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    mail.init_app(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Molimo prijavite se da pristupite ovoj stranici.'
    login_manager.login_message_category = 'info'

    # Register blueprints
    # Health check endpoint (simple route, not a blueprint)
    @app.route('/health')
    def health():
        """Health check endpoint for monitoring."""
        return {'status': 'ok'}, 200

    # TODO: Register blueprints when they are created in future stories
    # from app.routes import auth, dashboard, fakture, komitenti, artikli, admin
    # app.register_blueprint(auth.bp)
    # app.register_blueprint(dashboard.bp)
    # app.register_blueprint(fakture.bp)
    # app.register_blueprint(komitenti.bp)
    # app.register_blueprint(artikli.bp)
    # app.register_blueprint(admin.bp)

    return app
