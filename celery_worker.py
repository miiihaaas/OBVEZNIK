"""
Celery worker entry point.
Configures and runs the Celery worker for background tasks.
"""
from celery import Celery
from app import create_app

# Create Flask app
flask_app = create_app()

# Create Celery instance
celery = Celery(
    flask_app.import_name,
    broker=flask_app.config['CELERY_BROKER_URL'],
    backend=flask_app.config['CELERY_RESULT_BACKEND']
)

# Update Celery config from Flask config
celery.conf.update(flask_app.config)


class ContextTask(celery.Task):
    """Make celery tasks work with Flask app context."""

    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            return self.run(*args, **kwargs)


celery.Task = ContextTask
