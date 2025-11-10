"""Dashboard routes for pausalac users."""
from flask import Blueprint, render_template
from flask_login import login_required, current_user


dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def pausalac_dashboard():
    """
    Pausalac dashboard (placeholder for Story 1.3).

    Full implementation will be done in later stories.
    """
    return render_template('dashboard/pausalac.html', user=current_user)
