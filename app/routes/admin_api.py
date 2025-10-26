"""Admin API endpoints for AJAX autocomplete and lazy loading."""
from flask import Blueprint, request, jsonify
from flask_login import login_required
from app import db
from app.models.pausaln_firma import PausalnFirma
from app.utils.decorators import admin_required
from sqlalchemy import or_

admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')


@admin_api_bp.route('/firme/search', methods=['GET'])
@login_required
@admin_required
def search_firme():
    """
    Search pausaln firme with autocomplete and pagination (Admin only).

    Query Parameters:
        q (str, optional): Search query for naziv or PIB
        limit (int, optional): Maximum number of results (default: 20, max: 100)
        offset (int, optional): Pagination offset (default: 0)

    Returns:
        JSON: {
            "firme": [{"id": int, "naziv": str, "pib": str}, ...],
            "total": int,
            "has_more": bool
        }

    Example:
        GET /api/admin/firme/search?q=Test&limit=10
    """
    # Get query parameters
    search_query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 20)), 100)  # Max 100
    offset = int(request.args.get('offset', 0))

    # Build query
    query = PausalnFirma.query

    # Apply search filter if provided
    if search_query:
        search_pattern = f'%{search_query}%'
        query = query.filter(
            or_(
                PausalnFirma.naziv.ilike(search_pattern),
                PausalnFirma.pib.ilike(search_pattern)
            )
        )

    # Order by naziv
    query = query.order_by(PausalnFirma.naziv)

    # Get total count (before pagination)
    total = query.count()

    # Apply pagination
    firme = query.limit(limit).offset(offset).all()

    # Check if there are more results
    has_more = (offset + limit) < total

    # Serialize results
    results = [{
        'id': firma.id,
        'naziv': firma.naziv,
        'pib': firma.pib
    } for firma in firme]

    return jsonify({
        'firme': results,
        'total': total,
        'has_more': has_more
    })
