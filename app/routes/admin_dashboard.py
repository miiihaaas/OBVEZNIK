"""Admin Dashboard Blueprint for system-wide statistics and firm overview."""
from flask import Blueprint, render_template, request
from flask_login import login_required
from app.utils.decorators import admin_required
from app.services.dashboard_service import (
    get_admin_dashboard_stats,
    get_firma_list_with_stats
)
from datetime import date, timedelta


admin_dashboard_bp = Blueprint('admin_dashboard', __name__, url_prefix='/admin')


@admin_dashboard_bp.route('/dashboard', methods=['GET'])
@login_required
@admin_required
def dashboard():
    """
    Admin dashboard with system-wide statistics and firm overview.

    Query Parameters:
        date_from (str): Start date for filtering (YYYY-MM-DD format, default: first day of current month)
        date_to (str): End date for filtering (YYYY-MM-DD format, default: today)
        sort_by (str): Sort field ('naziv', 'broj_faktura', 'promet', 'limit', default: 'naziv')
        page (int): Page number for pagination (default: 1)
        search (str): Search query for filtering by naziv or PIB

    Returns:
        Rendered template with dashboard statistics and firma list
    """
    # Parse query parameters
    today = date.today()
    first_day_this_month = today.replace(day=1)

    # Date range parameters
    date_from_str = request.args.get('date_from')
    date_to_str = request.args.get('date_to')

    try:
        date_from = date.fromisoformat(date_from_str) if date_from_str else first_day_this_month
    except ValueError:
        date_from = first_day_this_month

    try:
        date_to = date.fromisoformat(date_to_str) if date_to_str else today
    except ValueError:
        date_to = today

    # Sorting and pagination parameters
    sort_by = request.args.get('sort_by', 'naziv')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_query = request.args.get('search', '').strip()

    # Validate sort_by parameter
    allowed_sort_fields = ['naziv', 'broj_faktura', 'promet', 'limit']
    if sort_by not in allowed_sort_fields:
        sort_by = 'naziv'

    # Get dashboard statistics
    stats = get_admin_dashboard_stats(date_from=date_from, date_to=date_to)

    # Get firma list with statistics
    firma_list, total_count = get_firma_list_with_stats(
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        page=page,
        per_page=per_page,
        search_query=search_query if search_query else None
    )

    # Calculate pagination info
    total_pages = (total_count + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        firma_list=firma_list,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        has_prev=has_prev,
        has_next=has_next,
        search_query=search_query
    )
