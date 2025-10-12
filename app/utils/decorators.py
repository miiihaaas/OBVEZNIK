"""Custom decorators for access control and authorization."""
from functools import wraps
from flask import abort
from flask_login import current_user


def admin_required(f):
    """
    Decorator to require admin role for accessing a route.

    Usage:
        @app.route('/admin/dashboard')
        @login_required
        @admin_required
        def admin_dashboard():
            return render_template('admin/dashboard.html')

    Returns:
        401 Unauthorized if user is not authenticated
        403 Forbidden if user is authenticated but not an admin
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated
        if not current_user.is_authenticated:
            return abort(401)  # Unauthorized

        # Check if user is admin
        if not current_user.is_admin():
            return abort(403)  # Forbidden

        return f(*args, **kwargs)

    return decorated_function
