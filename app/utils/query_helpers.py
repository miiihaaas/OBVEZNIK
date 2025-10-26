"""Query helper functions for tenant isolation.

These functions provide automatic filtering of database queries based on
the current user's firma_id. Admin users can access all data (god mode),
while pausalac users can only access data from their own firma.

Admin users can optionally select a specific firma context (session-based)
to view and manage data for that firma only. This allows admins to simulate
pausalac view or focus on specific firma data.

Usage:
    from app.utils.query_helpers import filter_by_firma, set_admin_firm_context
    from app.models.faktura import Faktura

    # This will automatically filter by firma_id for pausalac users
    fakture = filter_by_firma(Faktura.query).filter_by(status='izdata').all()

    # Admin can set firm context to view specific firma data
    set_admin_firm_context(firma_id=5)  # Admin now sees only firma 5 data
    clear_admin_firm_context()  # Admin returns to god mode (all data)
"""
from flask import session
from flask_login import current_user


def get_admin_selected_firma_id():
    """
    Get admin's currently selected firma_id from session.

    Admin users can optionally select a specific firma context (session-based)
    to view and manage data for that firma only.

    Returns:
        None: If no firma is selected (god mode) or not in session
        int: firma_id if admin has selected a specific firma context

    Examples:
        >>> get_admin_selected_firma_id()  # no firma selected
        None
        >>> get_admin_selected_firma_id()  # firma 5 selected
        5
    """
    return session.get('admin_selected_firma_id', None)


def get_user_firma_id():
    """
    Get firma_id for current user to apply tenant isolation.

    Admin users can optionally select a specific firma context (session-based).
    If no firma is selected, admin has full god mode access (returns None).

    Returns:
        None: If user is admin with no firma selected (god mode) or not authenticated
        int: firma_id if user is pausalac or admin with firma context selected

    Examples:
        >>> get_user_firma_id()  # as admin without firma selected
        None
        >>> get_user_firma_id()  # as admin with firma_id=5 selected
        5
        >>> get_user_firma_id()  # as pausalac with firma_id=3
        3
    """
    if not current_user.is_authenticated:
        return None  # Fallback (should not happen with @login_required)

    if current_user.is_admin():
        # Check if admin has selected a firma in session
        admin_selected_firma_id = get_admin_selected_firma_id()
        return admin_selected_firma_id  # None = god mode, int = filtered by firma

    return current_user.firma_id  # Pausalac always filtered by their firma


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


def set_admin_firm_context(firma_id):
    """
    Set admin's selected firma context in session.

    This allows admin users to view and manage data for a specific firma only,
    simulating a pausalac user's view or focusing on specific firma data.

    Args:
        firma_id (int): The ID of the firma to set as context

    Examples:
        >>> set_admin_firm_context(5)  # Admin now sees only firma 5 data
        >>> get_admin_selected_firma_id()
        5
    """
    session['admin_selected_firma_id'] = firma_id


def clear_admin_firm_context():
    """
    Clear admin's selected firma context from session.

    This returns the admin user to god mode (viewing all data across all firme).

    Examples:
        >>> clear_admin_firm_context()  # Admin returns to god mode
        >>> get_admin_selected_firma_id()
        None
    """
    session.pop('admin_selected_firma_id', None)
