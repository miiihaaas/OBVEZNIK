"""API routes for AJAX calls (NBS lookup, etc.)."""
from flask import Blueprint, jsonify, current_app
from flask_login import login_required
from app.services import nbs_komitent_service

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/nbs/firma/<pib>', methods=['GET'])
@login_required
def nbs_firma_lookup(pib):
    """
    NBS Komitent API lookup endpoint (AJAX).

    Args:
        pib: PIB (8 or 9 digits)

    Returns:
        JSON response with company data or error message
    """
    # Validate PIB format (8 or 9 digits)
    if not pib or len(pib) not in [8, 9] or not pib.isdigit():
        return jsonify({
            'error': 'Invalid PIB format',
            'message': 'PIB mora imati 8 ili 9 cifara.'
        }), 400

    # Call NBS service
    firma_data = nbs_komitent_service.fetch_company_by_pib(pib)

    if firma_data:
        return jsonify({
            'success': True,
            'data': firma_data
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': 'Firma nije pronađena u NBS bazi. Molimo unesite podatke ručno.'
        }), 200
