"""Dashboard routes for pausalac users."""
from flask import Blueprint, render_template, flash, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from datetime import date
import json

from app import db
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
    from flask import request

    # Get firma_id (works for both pausalac and admin in firm context)
    firma_id = get_user_firma_id()

    if not firma_id:
        # Admin in god mode - cannot access chart data without firm context
        return jsonify({'error': 'Firma context required'}), 403

    # Get months parameter from query string (default: 12)
    months = request.args.get('months', default=12, type=int)

    # Validate months parameter (1-24 months)
    if months < 1 or months > 24:
        months = 12

    # Get chart data
    chart_data = get_monthly_revenue_chart_data(firma_id, months=months)

    return jsonify(chart_data)


@dashboard_bp.route('/profil-firme', methods=['GET'])
@login_required
def profil_firme():
    """
    Profil firme view - prikazuje detalje firme (readonly/editable).

    Accessible by:
    - Pausalac users (uses current_user.firma_id)
    - Admin users in firm context (uses session['admin_selected_firma_id'])

    Displays:
    - Osnovni podaci firme (naziv, PIB, matični broj, adresa)
    - Kontakt informacije (telefon, email)
    - Računi (dinarski, devizni)
    - Faktura konfiguracija (prefiks, sufiks, brojač)
    - Limiti (rolling 365-day, calendar year) - readonly info
    """
    # Get firma_id (works for both pausalac and admin in firm context)
    firma_id = get_user_firma_id()

    if not firma_id:
        # Admin in god mode (no firm context) - redirect with error
        flash('Molimo selektujte firmu pre pristupa profilu firme.', 'warning')
        return redirect(url_for('admin_dashboard.dashboard'))

    # Load firma object
    firma = PausalnFirma.query.get_or_404(firma_id)

    return render_template('profil/view.html', firma=firma, rolling_limit=ROLLING_LIMIT_365_DAYS, yearly_limit=YEARLY_LIMIT)


@dashboard_bp.route('/profil-firme/edit', methods=['POST'])
@login_required
def profil_firme_edit():
    """
    Update profil firme - handle firma data updates with role-based field restrictions.

    Accessible by:
    - Pausalac users: Can update telefon, email, računi, prefiks/sufiks only
    - Admin users in firm context: Can update ALL fields including PIB, naziv, adresa

    Validates:
    - Email format
    - JSON structure for računi
    - Restricted fields based on user role

    Returns:
        Redirect to profil_firme view with success/error flash message
    """
    # Get firma_id (works for both pausalac and admin in firm context)
    firma_id = get_user_firma_id()

    if not firma_id:
        # Admin in god mode (no firm context) - redirect with error
        flash('Molimo selektujte firmu pre izmene podataka.', 'error')
        return redirect(url_for('admin_dashboard.dashboard'))

    # Load firma object
    firma = PausalnFirma.query.get_or_404(firma_id)

    # Define allowed fields based on user role
    if current_user.role == 'pausalac':
        allowed_fields = ['telefon', 'email', 'dinarski_racuni', 'devizni_racuni',
                         'prefiks_fakture', 'sufiks_fakture']
    else:  # admin
        allowed_fields = ['pib', 'maticni_broj', 'naziv', 'adresa', 'broj',
                         'postanski_broj', 'mesto', 'drzava', 'telefon', 'email',
                         'dinarski_racuni', 'devizni_racuni', 'prefiks_fakture', 'sufiks_fakture']

    try:
        # Update only allowed fields from form data
        for field in allowed_fields:
            if field in request.form:
                value = request.form[field]

                # Handle JSON fields (dinarski_racuni, devizni_racuni)
                if field in ['dinarski_racuni', 'devizni_racuni']:
                    try:
                        # Parse JSON string to Python object
                        json_value = json.loads(value)

                        # Validate dinarski_racuni is not empty
                        if field == 'dinarski_racuni' and len(json_value) == 0:
                            flash('Mora postojati bar jedan dinarski račun.', 'error')
                            return redirect(url_for('dashboard.profil_firme'))

                        setattr(firma, field, json_value)
                    except json.JSONDecodeError:
                        flash(f'Nevažeći format za polje {field}.', 'error')
                        return redirect(url_for('dashboard.profil_firme'))
                else:
                    # Regular text fields
                    setattr(firma, field, value)

        # Validate email format (basic check)
        if 'email' in allowed_fields and 'email' in request.form:
            email = request.form['email']
            if '@' not in email or '.' not in email:
                flash('Nevažeći format email adrese.', 'error')
                return redirect(url_for('dashboard.profil_firme'))

        # Commit changes to database
        db.session.commit()
        flash('Podaci firme uspešno ažurirani.', 'success')
        return redirect(url_for('dashboard.profil_firme'))

    except Exception as e:
        # Rollback on any database error
        db.session.rollback()
        flash(f'Greška pri čuvanju podataka: {str(e)}', 'error')
        return redirect(url_for('dashboard.profil_firme'))
