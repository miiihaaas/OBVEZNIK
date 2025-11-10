"""Dashboard routes for pausalac users."""
from flask import Blueprint, render_template, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import date

from app.models.pausaln_firma import PausalnFirma
from app.services.dashboard_service import (
    get_pausalac_dashboard_stats,
    get_pausalac_recent_fakture,
    calculate_rolling_limit_projections,
    get_monthly_revenue_chart_data,
    ROLLING_LIMIT_365_DAYS,
    YEARLY_LIMIT
)
from app.utils.query_helpers import get_user_firma_id


dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def pausalac_dashboard():
    """
    Pausalac dashboard with firma stats, rolling limit tracking, and recent invoices.

    Accessible by:
    - Pausalac users (uses current_user.firma_id)
    - Admin users in firm context (uses session['admin_selected_firma_id'])

    Displays:
    - Firma header (naziv, PIB, matični broj)
    - Rolling 365-day limit tracking widget with projections
    - Summary cards (invoices, revenue, komitenti, artikli)
    - Recent 10 invoices table
    """
    # Get firma_id (works for both pausalac and admin in firm context)
    firma_id = get_user_firma_id()

    if not firma_id:
        # Admin in god mode (no firm context) - should not access pausalac dashboard
        flash('Molimo selektujte firmu pre pristupa dashboard-u.', 'warning')
        return redirect(url_for('admin_dashboard.dashboard'))

    # Load firma object for header data
    firma = PausalnFirma.query.get_or_404(firma_id)

    # Get dashboard statistics
    stats = get_pausalac_dashboard_stats(firma_id)

    # Get recent fakture (limit: 10)
    recent_fakture = get_pausalac_recent_fakture(firma_id, limit=10)

    # Get rolling limit projections
    projections = calculate_rolling_limit_projections(firma_id)

    # Calculate progress bar percentage for yearly limit
    progress_percentage_godisnji = (stats['promet_tekuce_godine'] / YEARLY_LIMIT) * 100

    # Determine color class for yearly limit widget
    if progress_percentage_godisnji < 70:
        progress_color_godisnji = 'success'  # Green
    elif progress_percentage_godisnji < 90:
        progress_color_godisnji = 'warning'  # Yellow
    else:
        progress_color_godisnji = 'danger'   # Red

    # Calculate progress bar percentage for rolling 365-day limit
    progress_percentage = (stats['promet_365_dana'] / ROLLING_LIMIT_365_DAYS) * 100

    # Determine color class for rolling limit widget
    if progress_percentage < 70:
        progress_color = 'success'  # Green
    elif progress_percentage < 90:
        progress_color = 'warning'  # Yellow
    else:
        progress_color = 'danger'   # Red

    return render_template(
        'dashboard/pausalac.html',
        user=current_user,
        firma=firma,
        stats=stats,
        recent_fakture=recent_fakture,
        projections=projections,
        progress_percentage=progress_percentage,
        progress_color=progress_color,
        progress_percentage_godisnji=progress_percentage_godisnji,
        progress_color_godisnji=progress_color_godisnji,
        rolling_limit=ROLLING_LIMIT_365_DAYS,
        yearly_limit=YEARLY_LIMIT,
        current_year=date.today().year
    )


@dashboard_bp.route('/api/monthly-revenue-chart')
@login_required
def monthly_revenue_chart_api():
    """
    API endpoint for monthly revenue chart data.

    Returns JSON with labels and data for Chart.js line chart.

    Accessible by:
    - Pausalac users (uses current_user.firma_id)
    - Admin users in firm context (uses session['admin_selected_firma_id'])

    Returns:
        JSON: {
            'labels': ['Jan 2024', 'Feb 2024', ...],
            'data': [120000.50, 150000.00, ...]
        }
    """
    # Get firma_id (works for both pausalac and admin in firm context)
    firma_id = get_user_firma_id()

    if not firma_id:
        # Admin in god mode - cannot access chart data without firm context
        return jsonify({'error': 'Firma context required'}), 403

    # Get chart data for last 12 months
    chart_data = get_monthly_revenue_chart_data(firma_id, months=12)

    return jsonify(chart_data)
