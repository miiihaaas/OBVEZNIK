"""Query helper functions for tenant isolation.

These functions provide automatic filtering of database queries based on
the current user's firma_id. Admin users can access all data (god mode),
while pausalac users can only access data from their own firma.

Usage:
    from app.utils.query_helpers import filter_by_firma
    from app.models.faktura import Faktura

    # This will automatically filter by firma_id for pausalac users
    fakture = filter_by_firma(Faktura.query).filter_by(status='izdata').all()
"""
from flask_login import current_user


def get_user_firma_id():
    """
    Get firma_id for current user to apply tenant isolation.

    Returns:
        None: If user is admin (no filtering - god mode) or not authenticated
        int: firma_id if user is pausalac (filter by firma)

    Examples:
        >>> get_user_firma_id()  # as admin
        None
        >>> get_user_firma_id()  # as pausalac with firma_id=5
        5
    """
    if not current_user.is_authenticated:
        return None  # Fallback (should not happen with @login_required)

    if current_user.is_admin():
        return None  # Admin sees all data (god mode)

    return current_user.firma_id  # Pausalac sees only own firma data


def filter_by_firma(query):
    """
    Apply tenant isolation filter to SQLAlchemy query.

    This function automatically filters the query by firma_id based on the
    current user's role. Admin users get unfiltered access to all records,
    while pausalac users only see records from their own firma.

    Args:
        query: SQLAlchemy query object (e.g., Faktura.query)

    Returns:
        SQLAlchemy query object with firma_id filter applied (if applicable)

    Usage:
        # In a route:
        from app.utils.query_helpers import filter_by_firma
        from app.models.faktura import Faktura

        @fakture_bp.route('/fakture')
        @login_required
        def fakture_list():
            # Admin sees all fakture, pausalac sees only their firma's fakture
            fakture = filter_by_firma(Faktura.query).filter_by(status='izdata').all()
            return render_template('fakture/lista.html', fakture=fakture)

    Examples:
        >>> filter_by_firma(Faktura.query)  # as admin
        <Query returning all Faktura records>
        >>> filter_by_firma(Faktura.query)  # as pausalac with firma_id=5
        <Query filtered by firma_id=5>
    """
    firma_id = get_user_firma_id()

    if firma_id is None:
        # Admin user - return original query (no filtering)
        return query

    # Pausalac user - filter by firma_id
    return query.filter_by(firma_id=firma_id)
