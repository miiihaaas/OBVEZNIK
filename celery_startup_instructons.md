# Celery startup instrukcije za app u lokalu
* akitvirati venv pa zatim izvršiti sledeću komandu:
```powershell
celery -A celery_worker.celery worker --loglevel=info --pool=solo
```

# Celery startup instrukcije za app u prod
* kad provališ napiši isntrukcije