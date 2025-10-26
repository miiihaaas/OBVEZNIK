"""
Pytest configuration and fixtures for testing.
"""
import pytest
from app import create_app, db


@pytest.fixture(scope='function')
def app():
    """
    Create and configure a Flask app instance for testing.
    Function-scoped for complete test isolation.
    """
    app = create_app('testing')

    # Establish application context
    ctx = app.app_context()
    ctx.push()

    # Create all tables for testing
    db.create_all()

    yield app

    # Clean up: drop all tables
    db.drop_all()
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


@pytest.fixture(scope='function', autouse=True)
def clean_database(app):
    """
    Clean database between tests for isolation.
    Automatically used for all tests.
    """
    yield

    # Clean up: remove all data but keep tables
    # Expunge all objects from session to prevent DetachedInstanceError
    db.session.expunge_all()
    # Rollback any uncommitted transactions
    db.session.rollback()

    # Truncate all tables
    meta = db.metadata
    for table in reversed(meta.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()

    # Remove session to ensure clean state
    db.session.remove()
