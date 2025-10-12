"""Dashboard routes for pausalac and admin users."""
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.utils.decorators import admin_required


dashboard_bp = Blueprint('dashboard', __name__)
admin_dashboard_bp = Blueprint('admin_dashboard', __name__, url_prefix='/admin')


@dashboard_bp.route('/dashboard')
@login_required
def pausalac_dashboard():
    """
    Pausalac dashboard (placeholder for Story 1.3).

    Full implementation will be done in later stories.
    """
    return render_template('dashboard/pausalac.html', user=current_user)


@admin_dashboard_bp.route('/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """
    Admin dashboard (placeholder for Story 1.3).

    Full implementation will be done in later stories.
    """
    return render_template('admin/admin_dashboard.html', user=current_user)
