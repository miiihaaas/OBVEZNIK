"""
Celery worker entry point.
Configures and runs the Celery worker for background tasks.
"""
from celery import Celery
from celery.schedules import crontab
from app import create_app

# Create Flask app
flask_app = create_app()

# # Create Celery instance
# celery = Celery(
#     flask_app.import_name,
#     broker=flask_app.config['broker_url'],
#     backend=flask_app.config['result_backend']
# )

# # Update Celery config from Flask config
# celery.conf.update(flask_app.config)

# Create Celery instance  
celery = Celery(flask_app.import_name)

# Set Celery config from Flask config (Flask uses UPPERCASE, Celery 5+ uses lowercase)
celery.conf.broker_url = flask_app.config.get('BROKER_URL')
celery.conf.result_backend = flask_app.config.get('RESULT_BACKEND')
celery.conf.broker_connection_retry_on_startup = flask_app.config.get('BROKER_CONNECTION_RETRY_ON_STARTUP', True)

class ContextTask(celery.Task):
    """Make celery tasks work with Flask app context and request context."""

    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            with flask_app.test_request_context():
                return self.run(*args, **kwargs)


celery.Task = ContextTask

# Import tasks
from app.tasks.nbs_kursna_tasks import update_daily_kursna_lista
from app.tasks.pdf_tasks import generate_faktura_pdf_task
from app.tasks.email_tasks import send_faktura_email_task

# Register tasks with Celery
update_daily_kursna_lista_task = celery.task(update_daily_kursna_lista)
generate_faktura_pdf_task_async = celery.task(generate_faktura_pdf_task)
send_faktura_email_task_async = celery.task(
    send_faktura_email_task,
    bind=True,  # Bind task to get self parameter for retry logic
    max_retries=3,
    default_retry_delay=30  # Initial retry delay in seconds (exponential backoff: 30s, 60s, 120s)
)

# Configure Celery Beat schedule (using new format for Celery 5+)
celery.conf.beat_schedule = {
    'update-daily-kursna-lista': {
        'task': 'app.tasks.nbs_kursna_tasks.update_daily_kursna_lista',
        'schedule': crontab(hour=14, minute=0),  # Svaki dan u 14:00
    },
}
