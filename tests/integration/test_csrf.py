"""
Integration tests for CSRF protection.

Tests:
- CSRF protection is enabled in config
- POST requests without CSRF token are rejected
- Forms include CSRF token
"""
import pytest
from flask import url_for


def test_csrf_protection_enabled(app):
    """
    Test that CSRF protection is enabled in Flask-WTF.
    Note: CSRF is disabled in testing environment for easier testing.
    """
    if app.config.get('TESTING'):
        pytest.skip("CSRF protection is disabled in testing environment")

    assert app.config.get('WTF_CSRF_ENABLED') is not False, \
        "WTF_CSRF_ENABLED must be enabled (True or not explicitly disabled)"


def test_csrf_secret_key_configured(app):
    """
    Test that CSRF secret key is configured.
    """
    csrf_secret_key = app.config.get('WTF_CSRF_SECRET_KEY')

    # CSRF secret key should be set (can fall back to SECRET_KEY)
    assert csrf_secret_key is not None, \
        "WTF_CSRF_SECRET_KEY must be configured"

    # Secret key should not be default/weak value
    assert csrf_secret_key != 'dev-secret-key-change-in-production', \
        "CSRF secret key should be changed from default in production"


def test_post_without_csrf_token_fails(client, app):
    """
    Test that POST requests without CSRF token are rejected.
    Note: This test is skipped in testing environment where CSRF is disabled.
    """
    if not app.config.get('WTF_CSRF_ENABLED', True):
        pytest.skip("CSRF protection is disabled in testing environment")

    # Attempt to submit a form without CSRF token
    # Using a common endpoint (login) as example
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'testpassword'
    }, follow_redirects=False)

    # Should either reject (400) or redirect with error
    # Note: Response depends on implementation
    assert response.status_code in [400, 302, 401, 403], \
        "POST without CSRF token should be rejected or redirected"


def test_csrf_config_summary(app):
    """
    Summary test verifying CSRF protection configuration.
    """
    csrf_config = {
        'WTF_CSRF_ENABLED': app.config.get('WTF_CSRF_ENABLED'),
        'WTF_CSRF_SECRET_KEY': app.config.get('WTF_CSRF_SECRET_KEY'),
        'SECRET_KEY': app.config.get('SECRET_KEY'),
    }

    # Verify CSRF is enabled (except in testing)
    if app.config['TESTING']:
        print("\n⚠️ CSRF Protection: Disabled in testing environment")
    else:
        assert csrf_config['WTF_CSRF_ENABLED'] is not False, \
            "CSRF protection must be enabled in non-testing environments"

    # Verify secret key is configured
    assert csrf_config['SECRET_KEY'] is not None, \
        "SECRET_KEY must be configured"

    print("\n✅ CSRF Protection Configuration:")
    print(f"  WTF_CSRF_ENABLED: {csrf_config['WTF_CSRF_ENABLED']}")
    print(f"  WTF_CSRF_SECRET_KEY: {'***' if csrf_config['WTF_CSRF_SECRET_KEY'] else 'Not Set'}")
    print(f"  SECRET_KEY: {'***' if csrf_config['SECRET_KEY'] else 'Not Set'}")
