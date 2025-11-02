"""
Celery worker entry point.
Configures and runs the Celery worker for background tasks.
"""
from celery import Celery
from celery.schedules import crontab
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

# Import tasks
from app.tasks.nbs_kursna_tasks import update_daily_kursna_lista
from app.tasks.pdf_tasks import generate_faktura_pdf_task

# Register tasks with Celery
update_daily_kursna_lista_task = celery.task(update_daily_kursna_lista)
generate_faktura_pdf_task_async = celery.task(generate_faktura_pdf_task)

# Configure Celery Beat schedule (using new format for Celery 5+)
celery.conf.beat_schedule = {
    'update-daily-kursna-lista': {
        'task': 'app.tasks.nbs_kursna_tasks.update_daily_kursna_lista',
        'schedule': crontab(hour=14, minute=0),  # Svaki dan u 14:00
    },
}
