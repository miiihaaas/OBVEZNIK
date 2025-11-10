"""Dashboard service for admin dashboard statistics and aggregations."""
from app import db
from app.models.pausaln_firma import PausalnFirma
from app.models.faktura import Faktura
from app.models.user import User
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta, date
from typing import Optional, Dict, List, Tuple


# Constants
ROLLING_LIMIT_365_DAYS = 8_000_000  # RSD


def get_admin_dashboard_stats(date_from: Optional[date] = None, date_to: Optional[date] = None) -> Dict:
    """
    Get aggregated statistics for admin dashboard summary cards.

    Args:
        date_from: Start date for invoice filtering (default: first day of current month)
        date_to: End date for invoice filtering (default: today)

    Returns:
        dict: {
            'total_firme': int,
            'total_users': int,
            'total_fakture_period': int,
            'total_promet_period_rsd': Decimal
        }
    """
    # Set default date range: current month
    if date_from is None:
        date_from = date.today().replace(day=1)
    if date_to is None:
        date_to = date.today()

    # Total active firms
    total_firme = PausalnFirma.query.filter_by(is_active=True).count()

    # Total users
    total_users = User.query.count()

    # Aggregate invoices for the specified period (exclude stornirana)
    faktura_stats = db.session.query(
        func.count(Faktura.id).label('count'),
        func.coalesce(func.sum(Faktura.ukupan_iznos_rsd), 0).label('total_rsd')
    ).filter(
        and_(
            Faktura.datum_prometa >= date_from,
            Faktura.datum_prometa <= date_to,
            Faktura.status != 'stornirana'
        )
    ).first()

    return {
        'total_firme': total_firme,
        'total_users': total_users,
        'total_fakture_period': faktura_stats.count if faktura_stats else 0,
        'total_promet_period_rsd': faktura_stats.total_rsd if faktura_stats else 0
    }


def get_firma_list_with_stats(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort_by: str = 'naziv',
    page: int = 1,
    per_page: int = 20,
    search_query: Optional[str] = None
) -> Tuple[List[Dict], int]:
    """
    Get list of firms with aggregated statistics.

    Args:
        date_from: Start date for invoice filtering (default: first day of current month)
        date_to: End date for invoice filtering (default: today)
        sort_by: Field to sort by ('naziv', 'broj_faktura', 'promet', 'limit')
        page: Page number for pagination
        per_page: Number of items per page
        search_query: Search string for filtering by naziv or PIB

    Returns:
        tuple: (list of firma dicts with stats, total count)
    """
    # Set default date range
    if date_from is None:
        date_from = date.today().replace(day=1)
    if date_to is None:
        date_to = date.today()

    # Build base query with aggregations
    # Subquery for current period stats
    period_stats = db.session.query(
        Faktura.firma_id,
        func.count(Faktura.id).label('broj_faktura'),
        func.coalesce(func.sum(Faktura.ukupan_iznos_rsd), 0).label('promet_rsd'),
        func.max(Faktura.finalized_at).label('poslednja_aktivnost')
    ).filter(
        and_(
            Faktura.datum_prometa >= date_from,
            Faktura.datum_prometa <= date_to,
            Faktura.status != 'stornirana'
        )
    ).group_by(Faktura.firma_id).subquery()

    # Subquery for rolling 365-day promet (for limit calculation)
    date_365_days_ago = date.today() - timedelta(days=365)
    rolling_promet = db.session.query(
        Faktura.firma_id,
        func.coalesce(func.sum(Faktura.ukupan_iznos_rsd), 0).label('promet_365')
    ).filter(
        and_(
            Faktura.datum_prometa >= date_365_days_ago,
            Faktura.status != 'stornirana'
        )
    ).group_by(Faktura.firma_id).subquery()

    # Main query: join firms with period stats and rolling promet
    query = db.session.query(
        PausalnFirma.id,
        PausalnFirma.naziv,
        PausalnFirma.pib,
        func.coalesce(period_stats.c.broj_faktura, 0).label('broj_faktura'),
        func.coalesce(period_stats.c.promet_rsd, 0).label('promet_rsd'),
        period_stats.c.poslednja_aktivnost,
        func.coalesce(rolling_promet.c.promet_365, 0).label('promet_365')
    ).outerjoin(
        period_stats,
        PausalnFirma.id == period_stats.c.firma_id
    ).outerjoin(
        rolling_promet,
        PausalnFirma.id == rolling_promet.c.firma_id
    ).filter(
        PausalnFirma.is_active == True
    )

    # Apply search filter if provided
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                PausalnFirma.naziv.ilike(search_pattern),
                PausalnFirma.pib.like(search_pattern)
            )
        )

    # Get total count before pagination
    total_count = query.count()

    # Apply sorting
    if sort_by == 'naziv':
        query = query.order_by(PausalnFirma.naziv.asc())
    elif sort_by == 'broj_faktura':
        query = query.order_by(func.coalesce(period_stats.c.broj_faktura, 0).desc())
    elif sort_by == 'promet':
        query = query.order_by(func.coalesce(period_stats.c.promet_rsd, 0).desc())
    elif sort_by == 'limit':
        # Sort by remaining limit (descending, so highest remaining limit first)
        # Remaining limit = ROLLING_LIMIT_365_DAYS - promet_365
        query = query.order_by((ROLLING_LIMIT_365_DAYS - func.coalesce(rolling_promet.c.promet_365, 0)).desc())
    else:
        query = query.order_by(PausalnFirma.naziv.asc())

    # Apply pagination
    offset = (page - 1) * per_page
    results = query.limit(per_page).offset(offset).all()

    # Build result list with calculated rolling limits
    firma_list = []
    for row in results:
        # Calculate remaining limit from pre-fetched rolling promet
        preostali_limit = ROLLING_LIMIT_365_DAYS - float(row.promet_365 or 0)

        firma_list.append({
            'id': row.id,
            'naziv': row.naziv,
            'pib': row.pib,
            'broj_faktura': int(row.broj_faktura),
            'promet_rsd': float(row.promet_rsd),
            'preostali_limit_rsd': preostali_limit,
            'poslednja_aktivnost': row.poslednja_aktivnost
        })

    return firma_list, total_count


def calculate_firma_rolling_limit_remaining(firma_id: int) -> float:
    """
    Calculate remaining rolling 365-day limit for a firma.

    Rolling limit is 8,000,000 RSD per 365 days from today.

    Args:
        firma_id: ID of the firma

    Returns:
        float: Remaining limit in RSD (can be negative if over limit)
    """
    # Calculate promet for the last 365 days (excluding stornirana)
    date_365_days_ago = date.today() - timedelta(days=365)

    promet_365_days = db.session.query(
        func.coalesce(func.sum(Faktura.ukupan_iznos_rsd), 0)
    ).filter(
        and_(
            Faktura.firma_id == firma_id,
            Faktura.datum_prometa >= date_365_days_ago,
            Faktura.status != 'stornirana'
        )
    ).scalar()

    # Calculate remaining limit
    preostali_limit = ROLLING_LIMIT_365_DAYS - float(promet_365_days or 0)

    return preostali_limit
