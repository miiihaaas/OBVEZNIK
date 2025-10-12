# Test Documentation

## Test Credentials

### Seed Users

Run `python tests/seed_users.py` to create test users:

**Admin User:**
- Email: `admin@example.com`
- Password: `admin123`
- Role: admin

**Paušalac User:**
- Email: `pausalac@example.com`
- Password: `pausalac123`
- Role: pausalac
- Linked to: Test Paušalna Firma (PIB: 123456789)

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term --cov-report=html -v

# Run specific test file
pytest tests/unit/test_auth_service.py -v

# Run integration tests only
pytest tests/integration/ -v
```

## Test Structure

```
tests/
├── unit/                      # Unit tests
│   └── test_auth_service.py   # Authentication service tests
├── integration/               # Integration tests
│   └── test_auth_flow.py      # Login/logout flow tests
├── conftest.py                # pytest fixtures
└── seed_users.py              # Seed script for test users
```
