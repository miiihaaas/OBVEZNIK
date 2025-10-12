"""
Pytest configuration and fixtures for testing.
"""
import pytest
from app import create_app, db


@pytest.fixture(scope='session')
def app():
    """
    Create and configure a Flask app instance for testing.
    Session-scoped to reuse across all tests.
    """
    app = create_app('testing')

    # Establish application context
    ctx = app.app_context()
    ctx.push()

    yield app

    ctx.pop()


@pytest.fixture(scope='function')
def client(app):
    """
    Create a test client for the Flask app.
    Function-scoped for test isolation.
    """
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """
    Create a test CLI runner for the Flask app.
    """
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def init_database(app):
    """
    Initialize the database for testing.
    Creates all tables before the test and drops them after.
    """
    # Create all tables
    db.create_all()

    yield db

    # Clean up: drop all tables
    db.session.remove()
    db.drop_all()
