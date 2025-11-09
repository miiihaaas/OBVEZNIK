"""Routes for KPO (Knjiga Prometa Obveznika) management."""
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, flash, send_file, current_app
from flask_login import login_required, current_user
from app import db, limiter

kpo_bp = Blueprint('kpo', __name__, url_prefix='/kpo')
logger = logging.getLogger(__name__)


@kpo_bp.route('/')
@login_required
@limiter.limit("100 per minute")  # Prevent DoS via complex filters
def lista():
    """
    Display KPO knjiga with filters, sorting, and pagination.

    Query Parameters:
        - page: int - Page number (default: 1)
        - godina: int - Filter by year (optional)
        - datum_od: date - Filter by start date (YYYY-MM-DD)
        - datum_do: date - Filter by end date (YYYY-MM-DD)
        - komitent_search: str - Search by komitent name
        - status_filter: str - Filter by status ('izdata', 'stornirana', 'all', default: 'izdata')
        - valuta_filter: str - Filter by currency ('RSD', 'EUR', 'USD', 'GBP', 'CHF')
        - sort_by: str - Sort column ('datum_prometa', 'iznos_rsd', 'redni_broj')
        - sort_order: str - Sort order ('asc', 'desc')
        - firma_id: int - Admin-only: Filter by specific firma

    Returns:
        Rendered HTML template with paginated list of KPO entries
    """
    # Parse query parameters
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'datum_prometa')
    sort_order = request.args.get('sort_order', 'desc')

    # Build filters dictionary
    filters = {}

    # Godina filter
    if request.args.get('godina'):
        filters['godina'] = request.args.get('godina', type=int)
    else:
        # Default to current year
        filters['godina'] = datetime.now().year

    # Date filters
    datum_od_str = request.args.get('datum_od')
    if datum_od_str:
        try:
            filters['datum_od'] = datetime.strptime(datum_od_str, '%Y-%m-%d').date()
        except ValueError:
            logger.warning(f"Invalid datum_od format: {datum_od_str}, user: {current_user.email}")
            flash('Neispravan format datuma "od". Koristite YYYY-MM-DD format.', 'warning')

    datum_do_str = request.args.get('datum_do')
    if datum_do_str:
        try:
            filters['datum_do'] = datetime.strptime(datum_do_str, '%Y-%m-%d').date()
        except ValueError:
            logger.warning(f"Invalid datum_do format: {datum_do_str}, user: {current_user.email}")
            flash('Neispravan format datuma "do". Koristite YYYY-MM-DD format.', 'warning')

    # Komitent search filter
    if request.args.get('komitent_search'):
        filters['komitent_search'] = request.args.get('komitent_search').strip()

    # Status filter (default: 'izdata' per AC: 3)
    filters['status_filter'] = request.args.get('status_filter', 'izdata')

    # Valuta filter
    if request.args.get('valuta_filter'):
        filters['valuta_filter'] = request.args.get('valuta_filter')

    # Admin-only: firma filter
    if current_user.role == 'admin' and request.args.get('firma_id'):
        filters['firma_id'] = request.args.get('firma_id', type=int)

    # Call service layer to get paginated KPO entries
    from app.services.kpo_service import list_kpo_entries, calculate_total_promet_with_filters

    pagination = list_kpo_entries(
        user=current_user,
        filters=filters,
        page=page,
        per_page=20,
        sort_by=sort_by,
        sort_order=sort_order
    )

    # Calculate total promet (sum of iznos_rsd, excluding stornirane)
    total_promet = calculate_total_promet_with_filters(
        user=current_user,
        filters=filters
    )

    # Get list of available years for godina dropdown
    from app.models.kpo_entry import KPOEntry
    from sqlalchemy import distinct
    query = db.session.query(distinct(KPOEntry.godina)).order_by(KPOEntry.godina.desc())

    # Tenant isolation for godina list
    if current_user.role == 'pausalac':
        query = query.filter_by(firma_id=current_user.firma_id)
    elif current_user.role == 'admin' and filters.get('firma_id'):
        query = query.filter_by(firma_id=filters['firma_id'])

    available_years = [year[0] for year in query.all()]
    if not available_years:
        available_years = [datetime.now().year]

    # Get list of all pausaln firme for admin firma filter dropdown
    from app.models.pausaln_firma import PausalnFirma
    all_firme = []
    if current_user.role == 'admin':
        all_firme = PausalnFirma.query.filter_by(is_active=True).order_by(PausalnFirma.naziv).all()

    return render_template(
        'kpo/lista.html',
        pagination=pagination,
        total_promet=total_promet,
        available_years=available_years,
        all_firme=all_firme,
        current_filters=filters,
        sort_by=sort_by,
        sort_order=sort_order
    )


@kpo_bp.route('/export/pdf')
@login_required
def export_pdf():
    """
    Export KPO knjiga to PDF format.

    Query Parameters: Same as lista() route (for filtering)

    Returns:
        PDF file download
    """
    # Parse filters (same as lista route)
    filters = {}

    # Godina filter
    if request.args.get('godina'):
        filters['godina'] = request.args.get('godina', type=int)
    else:
        filters['godina'] = datetime.now().year

    # Date filters
    datum_od_str = request.args.get('datum_od')
    if datum_od_str:
        try:
            filters['datum_od'] = datetime.strptime(datum_od_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Neispravan format datuma "od".', 'warning')
            return redirect(url_for('kpo.lista'))

    datum_do_str = request.args.get('datum_do')
    if datum_do_str:
        try:
            filters['datum_do'] = datetime.strptime(datum_do_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Neispravan format datuma "do".', 'warning')
            return redirect(url_for('kpo.lista'))

    # Komitent search filter
    if request.args.get('komitent_search'):
        filters['komitent_search'] = request.args.get('komitent_search').strip()

    # Status filter
    filters['status_filter'] = request.args.get('status_filter', 'izdata')

    # Valuta filter
    if request.args.get('valuta_filter'):
        filters['valuta_filter'] = request.args.get('valuta_filter')

    # Admin-only: firma filter
    if current_user.role == 'admin' and request.args.get('firma_id'):
        filters['firma_id'] = request.args.get('firma_id', type=int)

    # Get KPO entries (no pagination for PDF export)
    from app.services.kpo_service import get_kpo_entries_list, calculate_total_promet_with_filters

    kpo_entries = get_kpo_entries_list(
        user=current_user,
        filters=filters,
        sort_by=request.args.get('sort_by', 'datum_prometa'),
        sort_order=request.args.get('sort_order', 'desc')
    )

    # Calculate total
    total_promet = calculate_total_promet_with_filters(
        user=current_user,
        filters=filters
    )

    # Get firma info
    from app.models.pausaln_firma import PausalnFirma
    if current_user.role == 'pausalac':
        firma = current_user.firma
    elif current_user.role == 'admin' and filters.get('firma_id'):
        firma = db.session.get(PausalnFirma, filters['firma_id'])
    else:
        firma = None  # God mode - no specific firma

    # Generate PDF
    from app.services.pdf_service import generate_kpo_pdf

    pdf_bytes = generate_kpo_pdf(
        kpo_entries=kpo_entries,
        firma=firma,
        filters=filters,
        total_promet=total_promet
    )

    # Send PDF as file download
    from io import BytesIO
    pdf_file = BytesIO(pdf_bytes)
    pdf_file.seek(0)

    filename = f"KPO_knjiga_{filters.get('godina', datetime.now().year)}.pdf"

    return send_file(
        pdf_file,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@kpo_bp.route('/export/csv')
@login_required
def export_csv():
    """
    Export KPO knjiga to CSV format (optional for MVP).

    Query Parameters: Same as lista() route (for filtering)

    Returns:
        CSV file download
    """
    # TODO: Implement CSV export (Phase 2)
    flash('CSV export nije jos implementiran. Koristite PDF export.', 'info')
    from flask import redirect, url_for
    return redirect(url_for('kpo.lista'))
