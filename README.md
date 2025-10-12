# Obveznik - Invoice Management System

Obveznik je sistem za upravljanje fakturama dizajniran za Marimar firmu. Omogućava kreiranje, slanje i praćenje faktura, upravljanje komitentima i artiklima, kao i integraciju sa APR-om za automatsko povlačenje podataka o komitentima.

## Tech Stack

- **Backend:** Flask 3.1+ (Python 3.9+)
- **Database:** MySQL 8.0+
- **ORM:** SQLAlchemy 2.0+
- **Migrations:** Alembic 1.13+
- **Authentication:** Flask-Login, Flask-Bcrypt
- **Task Queue:** Celery 5.3+ with Redis
- **PDF Generation:** WeasyPrint
- **Testing:** pytest 7.4+, pytest-flask 1.3+
- **CI/CD:** GitHub Actions

## Prerequisites

Prije pokretanja projekta, potrebno je da imaš instalirano:

- **Python 3.9+** - [Download Python](https://www.python.org/downloads/)
- **MySQL 8.0+** - [Download MySQL](https://dev.mysql.com/downloads/mysql/)
- **Redis 7.0+** - [Download Redis](https://redis.io/download) (opciono za MVP, obavezno za production)
- **Git** - [Download Git](https://git-scm.com/downloads)

## Local Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd OBVEZNIK
```

### 2. Create Virtual Environment

```bash
python -m venv venvObveznik
```

Aktiviraj virtual environment:

**Windows:**
```bash
venvObveznik\Scripts\activate
```

**Linux/Mac:**
```bash
source venvObveznik/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Kopiraj `.env.example` u `.env`:

```bash
cp .env.example .env
```

Edituj `.env` fajl i podesi environment variables:

```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/obveznik
REDIS_URL=redis://localhost:6379/0
```

### 5. Setup MySQL Database

Kreiraj MySQL database:

```sql
CREATE DATABASE obveznik CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Opciono, kreiraj test database:

```sql
CREATE DATABASE obveznik_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 6. Run Database Migrations

```bash
flask db upgrade
```

**Napomena:** Za sada nema modela, pa nema ni migracija. Prve migracije će se kreirati u Story 1.2.

### 7. Start Development Server

```bash
flask run
```

Ili:

```bash
python run.py
```

Aplikacija će biti dostupna na: `http://localhost:5000`

## Health Check

Testiraj da li aplikacija radi:

```bash
curl http://localhost:5000/health
```

Očekivani odgovor:

```json
{"status": "ok"}
```

## Running Tests

Pokreni sve testove:

```bash
pytest
```

Pokreni testove sa coverage report-om:

```bash
pytest --cov=app --cov-report=html
```

Coverage report će biti dostupan u `htmlcov/index.html`.

## Project Structure

```
OBVEZNIK/
├── app/                    # Flask application package
│   ├── __init__.py        # App factory
│   ├── models/            # SQLAlchemy models
│   ├── routes/            # Flask blueprints (routes)
│   ├── services/          # Business logic layer
│   ├── tasks/             # Celery background tasks
│   ├── forms/             # Flask-WTF forms
│   ├── templates/         # Jinja2 HTML templates
│   ├── static/            # CSS, JS, images
│   ├── utils/             # Utility functions
│   └── middleware/        # Custom middleware
├── migrations/            # Alembic database migrations
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── storage/              # Local file storage
│   └── fakture/         # PDF invoice storage
├── config.py             # Configuration classes
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
├── .env                 # Environment variables (git-ignored)
├── run.py               # Flask app entry point
└── celery_worker.py     # Celery worker entry point
```

## Development Workflow

1. **Create a new feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**

3. **Run tests:**
   ```bash
   pytest
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "Add your commit message"
   ```

5. **Push to remote:**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**

## CI/CD

GitHub Actions pipeline automatski pokreće testove na svaki push i pull request. Pipeline:

- Postavlja Python 3.9
- Instalira dependencies
- Pokreće MySQL i Redis servise
- Izvršava pytest testove
- Proverava da li je code coverage >= 70%

## Additional Commands

### Database Migrations

Kreiraj novu migraciju:

```bash
flask db migrate -m "Description of changes"
```

Primeni migracije:

```bash
flask db upgrade
```

Vrati migraciju:

```bash
flask db downgrade
```

### Celery Worker (za background tasks)

Pokreni Celery worker:

```bash
celery -A celery_worker.celery worker --loglevel=info
```

## Troubleshooting

### MySQL Connection Error

- Proveri da li je MySQL server pokrenut
- Proveri da li su credentials u `.env` fajlu tačni
- Proveri da li je database kreiran

### Redis Connection Error

- Proveri da li je Redis server pokrenut
- Za lokalni development, Redis nije obavezan za osnovnu funkcionalnost

### Import Errors

- Aktiviraj virtual environment: `venvObveznik\Scripts\activate`
- Reinstaliraj dependencies: `pip install -r requirements.txt`

## License

Proprietary - Marimar Internacionalni Transporti d.o.o.

## Contact

Za pitanja i podršku, kontaktiraj development team.
