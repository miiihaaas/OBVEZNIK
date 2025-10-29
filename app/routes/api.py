"""API routes for AJAX calls (NBS lookup, etc.)."""
from flask import Blueprint, jsonify, current_app, request
from flask_login import login_required
from datetime import date, datetime
from app.services import nbs_komitent_service
from app.services.nbs_kursna_service import get_kurs

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


@api_bp.route('/komitenti/search', methods=['GET'])
@login_required
def komitenti_search():
    """
    Komitenti autocomplete search endpoint (AJAX).

    Query Parameters:
        q: Search query string

    Returns:
        JSON array of matching komitenti [{id, naziv, pib, adresa}, ...]
        Limited to 20 results with tenant isolation
    """
    from flask import request
    from app.models.komitent import Komitent
    from app.utils.query_helpers import filter_by_firma

    query_string = request.args.get('q', '').strip()

    if not query_string:
        return jsonify([]), 200

    # Search komitenti by naziv (case-insensitive) with tenant isolation
    komitenti = (
        filter_by_firma(Komitent.query)
        .filter(Komitent.naziv.ilike(f'%{query_string}%'))
        .limit(20)
        .all()
    )

    # Format results for autocomplete
    results = [
        {
            'id': k.id,
            'naziv': k.naziv,
            'pib': k.pib,
            'adresa': f"{k.adresa} {k.broj}, {k.postanski_broj} {k.mesto}",
            'devizni_racuni': k.devizni_racuni  # Required for foreign currency invoices
        }
        for k in komitenti
    ]

    return jsonify(results), 200


@api_bp.route('/artikli/search', methods=['GET'])
@login_required
def artikli_search():
    """
    Artikli autocomplete search endpoint (AJAX).

    Query Parameters:
        q: Search query string

    Returns:
        JSON array of matching artikli [{id, naziv, podrazumevana_cena, jedinica_mere}, ...]
        Limited to 20 results with tenant isolation
    """
    from flask import request
    from app.models.artikal import Artikal
    from app.utils.query_helpers import filter_by_firma

    query_string = request.args.get('q', '').strip()

    if not query_string:
        return jsonify([]), 200

    # Search artikli by naziv (case-insensitive) with tenant isolation
    artikli = (
        filter_by_firma(Artikal.query)
        .filter(Artikal.naziv.ilike(f'%{query_string}%'))
        .limit(20)
        .all()
    )

    # Format results for autocomplete
    results = [
        {
            'id': a.id,
            'naziv': a.naziv,
            'podrazumevana_cena': str(a.podrazumevana_cena) if a.podrazumevana_cena else '0.00',
            'jedinica_mere': a.jedinica_mere or 'kom'
        }
        for a in artikli
    ]

    return jsonify(results), 200


@api_bp.route('/kursevi', methods=['GET'])
@login_required
def get_kursevi():
    """
    Get NBS exchange rates for currencies.

    Query Parameters:
        valuta: Currency code (EUR, USD, GBP, CHF) - optional, returns all if not specified
        datum: Date in YYYY-MM-DD format - optional, defaults to today

    Returns:
        JSON with exchange rates:
        {
            'EUR': '117.5432',
            'USD': '105.2341',
            'GBP': '135.6789',
            'CHF': '120.3456',
            'datum': '2025-01-15'
        }

        Or error response (503) if rates are not available
    """
    # Parse query parameters
    valuta = request.args.get('valuta', '').upper()
    datum_str = request.args.get('datum', '')

    # Parse datum (default to today)
    if datum_str:
        try:
            datum = datetime.strptime(datum_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'error': 'Invalid date format',
                'message': 'Datum mora biti u formatu YYYY-MM-DD.'
            }), 400
    else:
        datum = date.today()

    # Supported currencies
    supported_currencies = ['EUR', 'USD', 'GBP', 'CHF']

    # Validate valuta if specified
    if valuta and valuta not in supported_currencies:
        return jsonify({
            'error': 'Invalid currency',
            'message': f'Podržane valute: {", ".join(supported_currencies)}'
        }), 400

    # Determine which currencies to fetch
    currencies_to_fetch = [valuta] if valuta else supported_currencies

    # Fetch exchange rates
    kursevi = {}
    missing_currencies = []

    for currency in currencies_to_fetch:
        kurs = get_kurs(currency, datum)
        if kurs is not None:
            kursevi[currency] = str(kurs)
        else:
            missing_currencies.append(currency)

    # If any currencies are missing, return 503 error
    if missing_currencies:
        current_app.logger.warning(
            f"NBS kursevi not available for {missing_currencies} on {datum}"
        )
        return jsonify({
            'error': 'Exchange rates not available',
            'message': f'NBS kursevi nisu dostupni za {", ".join(missing_currencies)}. '
                      f'Molimo pokušajte kasnije ili unesite kurs ručno.',
            'missing_currencies': missing_currencies,
            'datum': str(datum)
        }), 503

    # Return successful response
    return jsonify({
        **kursevi,
        'datum': str(datum)
    }), 200
