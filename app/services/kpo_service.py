"""Business logic for KPO (Knjiga Prometa Obveznika) management."""
from datetime import datetime, timezone
from decimal import Decimal
import logging
from sqlalchemy import func
from app import db
from app.models.kpo_entry import KPOEntry
from app.models.faktura import Faktura
from app.models.komitent import Komitent

# Security logger for audit trail
security_logger = logging.getLogger('security')


def create_kpo_entry(faktura_id):
    """
    Kreira novi KPO entry za finalizovanu fakturu.

    Args:
        faktura_id: ID fakture koja se evidentira

    Returns:
        KPOEntry: Kreiran KPO entry objekat

    Raises:
        ValueError: Ako faktura nije izdata ili je profaktura
        ValueError: Ako KPO entry već postoji za ovu fakturu

    Logic:
        1. Load faktura with eager loading (komitent)
        2. Validate: status='izdata'
        3. Validate: tip_fakture != 'profaktura' (AC: 4)
        4. Calculate redni_broj: max(redni_broj) + 1 for firma_id and godina
        5. Extract godina from datum_prometa
        6. Create KPOEntry with denormalized data
        7. Commit and return
    """
    # Load faktura with eager loading
    faktura = db.session.query(Faktura).options(
        db.joinedload(Faktura.komitent)
    ).filter_by(id=faktura_id).first()

    if not faktura:
        raise ValueError(f"Faktura sa ID {faktura_id} ne postoji")

    # Validate: status='izdata'
    if faktura.status != 'izdata':
        raise ValueError(
            f"Faktura mora imati status 'izdata', trenutno ima status '{faktura.status}'"
        )

    # Validate: tip_fakture != 'profaktura' (AC: 4)
    if faktura.tip_fakture == 'profaktura':
        raise ValueError("Profakture se NE evidentiraju u KPO knjigu")

    # Check if KPO entry already exists
    existing_entry = KPOEntry.query.filter_by(faktura_id=faktura_id).first()
    if existing_entry:
        raise ValueError(
            f"KPO entry već postoji za fakturu {faktura.broj_fakture} (ID: {faktura_id})"
        )

    # Extract godina from datum_prometa
    godina = faktura.datum_prometa.year

    # Calculate redni_broj with SELECT FOR UPDATE lock to prevent race conditions
    # CRITICAL FIX (QA-PERF-001): Lock all KPO entries for this firma/godina
    # to ensure atomic redni_broj generation in concurrent scenarios
    db.session.query(KPOEntry).filter_by(
        firma_id=faktura.firma_id,
        godina=godina
    ).with_for_update().all()

    # Now calculate max safely within the lock
    max_redni_broj = db.session.query(
        func.max(KPOEntry.redni_broj)
    ).filter_by(
        firma_id=faktura.firma_id,
        godina=godina
    ).scalar()

    redni_broj = (max_redni_broj or 0) + 1

    # Generate opis from faktura stavke or default description
    opis = f"Faktura {faktura.broj_fakture}"
    if faktura.stavke:
        stavke_opis = ", ".join([stavka.naziv for stavka in faktura.stavke if stavka.naziv])
        if stavke_opis:
            opis = stavke_opis

    # Create KPO entry with denormalized data
    kpo_entry = KPOEntry(
        firma_id=faktura.firma_id,
        faktura_id=faktura.id,
        redni_broj=redni_broj,
        broj_fakture=faktura.broj_fakture,
        datum_prometa=faktura.datum_prometa,
        datum_dospeca=faktura.datum_dospeca,
        komitent_naziv=faktura.komitent.naziv,
        komitent_pib=faktura.komitent.pib,
        opis=opis,
        iznos_rsd=faktura.ukupan_iznos_rsd,
        valuta=faktura.valuta_fakture,
        status_fakture='izdata',
        godina=godina
    )

    db.session.add(kpo_entry)
    db.session.commit()

    security_logger.info(
        f"KPO entry created: redni_broj={redni_broj}/{godina}, "
        f"faktura={faktura.broj_fakture}, iznos={faktura.ukupan_iznos_rsd} RSD, "
        f"firma_id={faktura.firma_id}"
    )

    return kpo_entry


def update_kpo_entry_status(faktura_id, new_status):
    """
    Ažurira status KPO entry-a kada se faktura stornira.

    Args:
        faktura_id: ID fakture
        new_status: Novi status ('stornirana')

    Raises:
        ValueError: Ako KPO entry ne postoji za datu fakturu
    """
    kpo_entry = KPOEntry.query.filter_by(faktura_id=faktura_id).first()

    if not kpo_entry:
        raise ValueError(
            f"KPO entry ne postoji za fakturu ID {faktura_id}"
        )

    old_status = kpo_entry.status_fakture
    kpo_entry.status_fakture = new_status
    db.session.commit()

    security_logger.info(
        f"KPO entry status updated: redni_broj={kpo_entry.redni_broj}/{kpo_entry.godina}, "
        f"faktura={kpo_entry.broj_fakture}, status changed from '{old_status}' to '{new_status}', "
        f"firma_id={kpo_entry.firma_id}"
    )


def get_kpo_entries_for_firma(firma_id, godina=None, status_filter='izdata'):
    """
    Vraća listu KPO entries za datu firmu.

    Args:
        firma_id: ID paušalne firme
        godina: Opciono - filter po godini
        status_filter: Filter po statusu ('izdata', 'stornirana', 'all')

    Returns:
        List[KPOEntry]: Lista KPO entries sortirana po redni_broj ASC
    """
    query = KPOEntry.query.filter_by(firma_id=firma_id)

    # Filter by godina if provided
    if godina is not None:
        query = query.filter_by(godina=godina)

    # Filter by status if not 'all'
    if status_filter != 'all':
        query = query.filter_by(status_fakture=status_filter)

    # Order by redni_broj ASC
    kpo_entries = query.order_by(KPOEntry.redni_broj.asc()).all()

    return kpo_entries


def calculate_total_promet(firma_id, godina, status_filter='izdata'):
    """
    Kalkuliše ukupan promet za firmu u datoj godini.

    Args:
        firma_id: ID paušalne firme
        godina: Godina za proračun
        status_filter: Filter po statusu (default: samo 'izdata', AC: 3)

    Returns:
        Decimal: Ukupan promet u RSD (suma iznos_rsd)

    Note:
        Stornirane fakture se NE uključuju u promet (AC: 3)
    """
    query = db.session.query(
        func.sum(KPOEntry.iznos_rsd)
    ).filter_by(
        firma_id=firma_id,
        godina=godina
    )

    # Filter by status if not 'all'
    if status_filter != 'all':
        query = query.filter_by(status_fakture=status_filter)

    total = query.scalar()

    # Return 0.00 if no entries found
    return total or Decimal('0.00')


def list_kpo_entries(user, filters, page, per_page, sort_by='datum_prometa', sort_order='desc'):
    """
    Lista KPO entries sa paginacijom, filterima i sortiranjem.
    
    Args:
        user: Current user object (za tenant isolation)
        filters: Dict sa filterima (godina, datum_od, datum_do, komitent_search, status_filter, valuta_filter, firma_id)
        page: Page number
        per_page: Items per page
        sort_by: Column to sort by ('datum_prometa', 'iznos_rsd', 'redni_broj')
        sort_order: Sort order ('asc', 'desc')
    
    Returns:
        Pagination object sa KPO entries
    """
    # Base query
    query = KPOEntry.query
    
    # Tenant isolation (CRITICAL)
    if user.role == 'pausalac':
        query = query.filter_by(firma_id=user.firma_id)
    elif user.role == 'admin' and filters.get('firma_id'):
        query = query.filter_by(firma_id=filters['firma_id'])
    # Else: Admin god mode - no firma filter
    
    # Filter by godina
    if filters.get('godina'):
        query = query.filter_by(godina=filters['godina'])
    
    # Filter by datum_od
    if filters.get('datum_od'):
        query = query.filter(KPOEntry.datum_prometa >= filters['datum_od'])
    
    # Filter by datum_do
    if filters.get('datum_do'):
        query = query.filter(KPOEntry.datum_prometa <= filters['datum_do'])
    
    # Filter by komitent_search (LIKE search on komitent_naziv)
    if filters.get('komitent_search'):
        search_pattern = f"%{filters['komitent_search']}%"
        query = query.filter(KPOEntry.komitent_naziv.ilike(search_pattern))
    
    # Filter by status (default: 'izdata')
    status_filter = filters.get('status_filter', 'izdata')
    if status_filter != 'all':
        query = query.filter_by(status_fakture=status_filter)
    
    # Filter by valuta
    if filters.get('valuta_filter'):
        query = query.filter_by(valuta=filters['valuta_filter'])
    
    # Sorting
    if sort_by == 'datum_prometa':
        sort_column = KPOEntry.datum_prometa
    elif sort_by == 'iznos_rsd':
        sort_column = KPOEntry.iznos_rsd
    elif sort_by == 'redni_broj':
        sort_column = KPOEntry.redni_broj
    else:
        sort_column = KPOEntry.datum_prometa  # Default
    
    if sort_order == 'asc':
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    # Pagination
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return pagination


def get_kpo_entries_list(user, filters, sort_by='datum_prometa', sort_order='desc'):
    """
    Vraća listu KPO entries bez paginacije (za export).
    
    Args:
        user: Current user object (za tenant isolation)
        filters: Dict sa filterima (isti kao list_kpo_entries)
        sort_by: Column to sort by
        sort_order: Sort order
    
    Returns:
        List[KPOEntry]: Lista svih KPO entries
    """
    # Base query
    query = KPOEntry.query
    
    # Tenant isolation (CRITICAL)
    if user.role == 'pausalac':
        query = query.filter_by(firma_id=user.firma_id)
    elif user.role == 'admin' and filters.get('firma_id'):
        query = query.filter_by(firma_id=filters['firma_id'])
    # Else: Admin god mode - no firma filter
    
    # Filter by godina
    if filters.get('godina'):
        query = query.filter_by(godina=filters['godina'])
    
    # Filter by datum_od
    if filters.get('datum_od'):
        query = query.filter(KPOEntry.datum_prometa >= filters['datum_od'])
    
    # Filter by datum_do
    if filters.get('datum_do'):
        query = query.filter(KPOEntry.datum_prometa <= filters['datum_do'])
    
    # Filter by komitent_search
    if filters.get('komitent_search'):
        search_pattern = f"%{filters['komitent_search']}%"
        query = query.filter(KPOEntry.komitent_naziv.ilike(search_pattern))
    
    # Filter by status
    status_filter = filters.get('status_filter', 'izdata')
    if status_filter != 'all':
        query = query.filter_by(status_fakture=status_filter)
    
    # Filter by valuta
    if filters.get('valuta_filter'):
        query = query.filter_by(valuta=filters['valuta_filter'])
    
    # Sorting
    if sort_by == 'datum_prometa':
        sort_column = KPOEntry.datum_prometa
    elif sort_by == 'iznos_rsd':
        sort_column = KPOEntry.iznos_rsd
    elif sort_by == 'redni_broj':
        sort_column = KPOEntry.redni_broj
    else:
        sort_column = KPOEntry.datum_prometa  # Default
    
    if sort_order == 'asc':
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    # Return all entries (no pagination)
    return query.all()


def calculate_total_promet_with_filters(user, filters):
    """
    Kalkuliše ukupan promet sa filterima (extended verzija calculate_total_promet).
    
    Args:
        user: Current user object (za tenant isolation)
        filters: Dict sa filterima (godina, datum_od, datum_do, status_filter, valuta_filter, firma_id)
    
    Returns:
        Decimal: Ukupan promet u RSD (suma iznos_rsd)
    
    Note:
        Stornirane fakture se NE uključuju u promet (ako status_filter != 'all')
    """
    # Base query
    query = db.session.query(func.sum(KPOEntry.iznos_rsd))
    
    # Tenant isolation (CRITICAL)
    if user.role == 'pausalac':
        query = query.filter_by(firma_id=user.firma_id)
    elif user.role == 'admin' and filters.get('firma_id'):
        query = query.filter_by(firma_id=filters['firma_id'])
    # Else: Admin god mode - no firma filter
    
    # Filter by godina
    if filters.get('godina'):
        query = query.filter_by(godina=filters['godina'])
    
    # Filter by datum_od
    if filters.get('datum_od'):
        query = query.filter(KPOEntry.datum_prometa >= filters['datum_od'])
    
    # Filter by datum_do
    if filters.get('datum_do'):
        query = query.filter(KPOEntry.datum_prometa <= filters['datum_do'])
    
    # Filter by komitent_search
    if filters.get('komitent_search'):
        search_pattern = f"%{filters['komitent_search']}%"
        query = query.filter(KPOEntry.komitent_naziv.ilike(search_pattern))
    
    # Filter by status (default: 'izdata' - excludes stornirane)
    status_filter = filters.get('status_filter', 'izdata')
    if status_filter != 'all':
        query = query.filter_by(status_fakture=status_filter)
    
    # Filter by valuta
    if filters.get('valuta_filter'):
        query = query.filter_by(valuta=filters['valuta_filter'])
    
    total = query.scalar()
    
    # Return 0.00 if no entries found
    return total or Decimal('0.00')
