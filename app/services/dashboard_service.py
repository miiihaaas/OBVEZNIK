"""Dashboard service for admin dashboard statistics and aggregations."""
from app import db
from app.models.pausaln_firma import PausalnFirma
from app.models.faktura import Faktura
from app.models.user import User
from app.models.komitent import Komitent
from app.models.artikal import Artikal
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta, date
from typing import Optional, Dict, List, Tuple


# Constants
ROLLING_LIMIT_365_DAYS = 8_000_000  # RSD - Rolling 365-day limit
YEARLY_LIMIT = 6_000_000  # RSD - Calendar year limit (Jan 1 - Dec 31)


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


def get_pausalac_dashboard_stats(firma_id: int) -> Dict:
    """
    Get aggregated statistics for pausalac dashboard.

    Args:
        firma_id: ID of the firma

    Returns:
        dict: {
            'broj_faktura_ovog_meseca': int,
            'promet_ovog_meseca': float,
            'promet_tekuce_godine': float,
            'preostali_limit_godisnji': float,
            'promet_365_dana': float,
            'preostali_limit_365': float,
            'broj_komitenata': int,
            'broj_artikala': int
        }
    """
    # Date ranges
    today = date.today()
    first_day_of_month = today.replace(day=1)
    first_day_of_year = today.replace(month=1, day=1)
    date_365_days_ago = today - timedelta(days=365)

    # Aggregate fakture for current month (excluding stornirana)
    faktura_stats_month = db.session.query(
        func.count(Faktura.id).label('count'),
        func.coalesce(func.sum(Faktura.ukupan_iznos_rsd), 0).label('total_rsd')
    ).filter(
        and_(
            Faktura.firma_id == firma_id,
            Faktura.datum_prometa >= first_day_of_month,
            Faktura.datum_prometa <= today,
            Faktura.status != 'stornirana'
        )
    ).first()

    # Aggregate fakture for current calendar year (excluding stornirana)
    promet_tekuce_godine = db.session.query(
        func.coalesce(func.sum(Faktura.ukupan_iznos_rsd), 0)
    ).filter(
        and_(
            Faktura.firma_id == firma_id,
            Faktura.datum_prometa >= first_day_of_year,
            Faktura.datum_prometa <= today,
            Faktura.status != 'stornirana'
        )
    ).scalar()

    # Calculate remaining yearly limit
    preostali_limit_godisnji = YEARLY_LIMIT - float(promet_tekuce_godine or 0)

    # Aggregate fakture for rolling 365 days (excluding stornirana)
    promet_365_days = db.session.query(
        func.coalesce(func.sum(Faktura.ukupan_iznos_rsd), 0)
    ).filter(
        and_(
            Faktura.firma_id == firma_id,
            Faktura.datum_prometa >= date_365_days_ago,
            Faktura.datum_prometa <= today,
            Faktura.status != 'stornirana'
        )
    ).scalar()

    # Calculate remaining rolling 365-day limit
    preostali_limit_365 = ROLLING_LIMIT_365_DAYS - float(promet_365_days or 0)

    # Count komitenti
    broj_komitenata = Komitent.query.filter_by(firma_id=firma_id).count()

    # Count artikli
    broj_artikala = Artikal.query.filter_by(firma_id=firma_id).count()

    return {
        'broj_faktura_ovog_meseca': faktura_stats_month.count if faktura_stats_month else 0,
        'promet_ovog_meseca': float(faktura_stats_month.total_rsd) if faktura_stats_month else 0.0,
        'promet_tekuce_godine': float(promet_tekuce_godine or 0),
        'preostali_limit_godisnji': preostali_limit_godisnji,
        'promet_365_dana': float(promet_365_days or 0),
        'preostali_limit_365': preostali_limit_365,
        'broj_komitenata': broj_komitenata,
        'broj_artikala': broj_artikala
    }


def get_pausalac_recent_fakture(firma_id: int, limit: int = 10) -> List[Faktura]:
    """
    Get most recent fakture for a firma.

    Args:
        firma_id: ID of the firma
        limit: Number of fakture to return (default: 10)

    Returns:
        List of Faktura objects with komitent relationship loaded
    """
    fakture = Faktura.query.options(
        joinedload(Faktura.komitent)
    ).filter(
        Faktura.firma_id == firma_id
    ).order_by(
        Faktura.datum_prometa.desc(),
        Faktura.created_at.desc()
    ).limit(limit).all()

    return fakture


def calculate_rolling_limit_projections(firma_id: int) -> Dict:
    """
    Calculate rolling limit projections for 7, 15, and 30 days using REAL data.

    Uses sliding window approach: shifts the rolling 365-day window forward by N days
    to simulate what the limit will be in the future based on ACTUAL data from DB.

    Logic:
    - Current rolling 365: (today - 365) to today
    - Projection for +7 days: (today - 358) to (today + 7) → includes future invoices
    - Projection for +15 days: (today - 350) to (today + 15) → includes future invoices
    - Projection for +30 days: (today - 335) to (today + 30) → includes future invoices

    This gives REAL projections based on actual DB data, including future-dated invoices.

    Args:
        firma_id: ID of the firma

    Returns:
        dict: {
            'preostali_limit': float,
            'projekcija_7_dana': float,
            'projekcija_15_dana': float,
            'projekcija_30_dana': float,
            'upozorenje_7_dana': bool,
            'upozorenje_15_dana': bool,
            'upozorenje_30_dana': bool
        }
    """
    today = date.today()

    # Current rolling 365-day promet (baseline)
    # Only includes invoices up to today (not future-dated invoices)
    date_365_days_ago = today - timedelta(days=365)
    promet_365_current = db.session.query(
        func.coalesce(func.sum(Faktura.ukupan_iznos_rsd), 0)
    ).filter(
        and_(
            Faktura.firma_id == firma_id,
            Faktura.datum_prometa >= date_365_days_ago,
            Faktura.datum_prometa <= today,
            Faktura.status != 'stornirana'
        )
    ).scalar()

    preostali_limit_current = ROLLING_LIMIT_365_DAYS - float(promet_365_current or 0)

    # Projection for +7 days: rolling window from (today - 358) to (today + 7)
    # This simulates: old invoices falling off + future invoices entering the window
    start_7 = today - timedelta(days=358)
    end_7 = today + timedelta(days=7)
    promet_7 = db.session.query(
        func.coalesce(func.sum(Faktura.ukupan_iznos_rsd), 0)
    ).filter(
        and_(
            Faktura.firma_id == firma_id,
            Faktura.datum_prometa >= start_7,
            Faktura.datum_prometa <= end_7,
            Faktura.status != 'stornirana'
        )
    ).scalar()
    projekcija_7 = ROLLING_LIMIT_365_DAYS - float(promet_7 or 0)

    # Projection for +15 days: rolling window from (today - 350) to (today + 15)
    start_15 = today - timedelta(days=350)
    end_15 = today + timedelta(days=15)
    promet_15 = db.session.query(
        func.coalesce(func.sum(Faktura.ukupan_iznos_rsd), 0)
    ).filter(
        and_(
            Faktura.firma_id == firma_id,
            Faktura.datum_prometa >= start_15,
            Faktura.datum_prometa <= end_15,
            Faktura.status != 'stornirana'
        )
    ).scalar()
    projekcija_15 = ROLLING_LIMIT_365_DAYS - float(promet_15 or 0)

    # Projection for +30 days: rolling window from (today - 335) to (today + 30)
    start_30 = today - timedelta(days=335)
    end_30 = today + timedelta(days=30)
    promet_30 = db.session.query(
        func.coalesce(func.sum(Faktura.ukupan_iznos_rsd), 0)
    ).filter(
        and_(
            Faktura.firma_id == firma_id,
            Faktura.datum_prometa >= start_30,
            Faktura.datum_prometa <= end_30,
            Faktura.status != 'stornirana'
        )
    ).scalar()
    projekcija_30 = ROLLING_LIMIT_365_DAYS - float(promet_30 or 0)

    return {
        'preostali_limit': preostali_limit_current,
        'projekcija_7_dana': projekcija_7,
        'projekcija_15_dana': projekcija_15,
        'projekcija_30_dana': projekcija_30,
        'upozorenje_7_dana': projekcija_7 < 0,
        'upozorenje_15_dana': projekcija_15 < 0,
        'upozorenje_30_dana': projekcija_30 < 0
    }


def get_monthly_revenue_chart_data(firma_id: int, months: int = 12) -> Dict:
    """
    Get monthly revenue data for chart visualization.

    Returns revenue aggregated by month for the last N months.

    Args:
        firma_id: ID of the firma
        months: Number of months to include (default: 12)

    Returns:
        dict: {
            'labels': List[str],  # Month labels (e.g., "Jan 2025", "Feb 2025")
            'data': List[float]   # Revenue values for each month
        }
    """
    from dateutil.relativedelta import relativedelta
    today = date.today()

    # Calculate start date (N months ago)
    start_date = today - relativedelta(months=months)

    # Query monthly aggregates
    # Extract year and month from datum_prometa, group by them
    from sqlalchemy import extract

    monthly_data = db.session.query(
        extract('year', Faktura.datum_prometa).label('year'),
        extract('month', Faktura.datum_prometa).label('month'),
        func.coalesce(func.sum(Faktura.ukupan_iznos_rsd), 0).label('revenue')
    ).filter(
        and_(
            Faktura.firma_id == firma_id,
            Faktura.datum_prometa >= start_date,
            Faktura.status != 'stornirana'
        )
    ).group_by(
        extract('year', Faktura.datum_prometa),
        extract('month', Faktura.datum_prometa)
    ).order_by(
        extract('year', Faktura.datum_prometa).asc(),
        extract('month', Faktura.datum_prometa).asc()
    ).all()

    # Build complete list of months (fill in missing months with 0)
    labels = []
    data = []

    # Create map of existing data
    revenue_map = {}
    for row in monthly_data:
        year_month_key = f"{int(row.year)}-{int(row.month):02d}"
        revenue_map[year_month_key] = float(row.revenue)

    # Generate last N months
    current_date = today.replace(day=1)
    for i in range(months):
        # Go back i months
        month_date = current_date - relativedelta(months=i)

        # Format label
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun', 'Jul', 'Avg', 'Sep', 'Okt', 'Nov', 'Dec']
        label = f"{month_names[month_date.month - 1]} {month_date.year}"

        # Get revenue for this month (0 if not found)
        year_month_key = f"{month_date.year}-{month_date.month:02d}"
        revenue = revenue_map.get(year_month_key, 0.0)

        labels.insert(0, label)  # Insert at beginning to maintain chronological order
        data.insert(0, revenue)

    return {
        'labels': labels,
        'data': data
    }
