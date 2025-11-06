"""Business logic for Faktura (Invoice) management."""
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from flask import request
from app import db
from app.models.faktura import Faktura
from app.models.faktura_stavka import FakturaStavka
from app.models.pausaln_firma import PausalnFirma
from app.services.nbs_kursna_service import get_kurs

# Security logger for audit trail
security_logger = logging.getLogger('security')


def generate_broj_fakture(firma, tip_fakture='standardna'):
    """
    Generate the next invoice number based on tip fakture, firma's prefix, counter, and suffix.

    Args:
        firma: PausalnFirma instance
        tip_fakture: str - Type of invoice ('standardna', 'profaktura', 'avansna')

    Returns:
        str: Generated invoice number
            - Standardna: "{prefiks}{brojac}{sufiks}" (e.g., "MK-0001/2025-PS")
            - Profaktura: "{prefiks}PRO{brojac}{sufiks}" (e.g., "MK-PRO-0001/2025-PS")
            - Avansna: "{prefiks}AVN{brojac}{sufiks}" (e.g., "MK-AVN-0001/2025-PS")

    Note:
        Does NOT increment the counter - that happens only during finalization.
    """
    prefiks = firma.prefiks_fakture or ''
    sufiks = firma.sufiks_fakture or ''

    if tip_fakture == 'profaktura':
        brojac = str(firma.brojac_profakture).zfill(4)  # Pad with zeros (e.g., 0001)
        return f"{prefiks}PRO{brojac}{sufiks}"
    elif tip_fakture == 'avansna':
        # Priprema za Story 4.3 - avansne fakture
        brojac = str(getattr(firma, 'brojac_avansne', 1)).zfill(4)
        return f"{prefiks}AVN{brojac}{sufiks}"
    else:  # standardna
        brojac = str(firma.brojac_fakture).zfill(4)  # Pad with zeros (e.g., 0001)
        return f"{prefiks}{brojac}{sufiks}"


def calculate_datum_dospeca(datum_prometa, valuta_placanja):
    """
    Calculate due date based on transaction date and payment term.

    If the due date falls on a weekend (Saturday/Sunday), move it to the next Monday.

    Args:
        datum_prometa: date - Transaction date
        valuta_placanja: int - Payment term in days

    Returns:
        date: Calculated due date (adjusted for weekends)

    Note:
        TODO Phase 2: Check for state holidays (za sada samo vikend)
    """
    datum_dospeca = datum_prometa + timedelta(days=valuta_placanja)

    # Check if due date falls on weekend
    # weekday(): Monday=0, Sunday=6
    if datum_dospeca.weekday() == 5:  # Saturday
        datum_dospeca += timedelta(days=2)  # Move to Monday
    elif datum_dospeca.weekday() == 6:  # Sunday
        datum_dospeca += timedelta(days=1)  # Move to Monday

    return datum_dospeca


def create_faktura(data, user):
    """
    Create a new invoice (faktura) with line items.

    Args:
        data: dict - Form data containing invoice fields and stavke
        user: User - Current user creating the invoice

    Returns:
        Faktura: Created faktura instance (status='draft')

    Raises:
        ValueError: If data is invalid

    Business Rules:
        - Invoice is created with status='draft'
        - Draft invoices get temporary number DRAFT-{id} (allows multiple drafts)
        - Final invoice number is assigned during finalization
        - Counter is NOT incremented until finalization
        - Due date is calculated with weekend adjustment
        - Total amount is calculated as sum of all line items
    """
    firma = user.firma

    # Draft invoices get temporary number (will be replaced with DRAFT-{id} after flush)
    # Final number is assigned during finalization
    broj_fakture = "DRAFT-TEMP"

    # Calculate due date
    datum_dospeca = calculate_datum_dospeca(
        data.get('datum_prometa'),
        data.get('valuta_placanja')
    )

    # Determine if this is a foreign currency invoice
    tip_fakture = data.get('tip_fakture', 'standardna')

    # Validate devizna fakture MUST have valid foreign currency
    if tip_fakture == 'devizna':
        valuta_fakture = data.get('valuta_fakture')
        if not valuta_fakture or valuta_fakture not in ['EUR', 'USD', 'GBP', 'CHF']:
            raise ValueError(
                "Devizna faktura mora imati valutu (EUR, USD, GBP ili CHF). "
                "Molimo izaberite valutu."
            )
    else:
        valuta_fakture = 'RSD'

    # For foreign currency invoices, fetch NBS exchange rate
    srednji_kurs = None
    jezik = 'sr'  # Default to Serbian

    if tip_fakture == 'devizna':
        # Validate komitent has at least one devizni račun for foreign currency invoices
        from app.models.komitent import Komitent
        komitent = db.session.get(Komitent, data.get('komitent_id'))
        if not komitent:
            raise ValueError("Komitent nije pronađen.")
        # SEC-001: Tenant isolation - validate komitent belongs to user's firma
        if komitent.firma_id != firma.id:
            raise ValueError("Komitent ne pripada vašoj firmi.")
        if not komitent.devizni_racuni or len(komitent.devizni_racuni) == 0:
            raise ValueError(
                "Komitent mora imati bar jedan devizni račun za devizne fakture. "
                "Molimo ažurirajte podatke komitenta pre kreiranja devizne fakture."
            )

        datum_prometa = data.get('datum_prometa')

        # Check if manual srednji_kurs is provided in form (user override)
        if data.get('srednji_kurs'):
            srednji_kurs = Decimal(str(data.get('srednji_kurs')))
        else:
            # Fetch from NBS
            srednji_kurs = get_kurs(valuta_fakture, datum_prometa)

        # If no kurs available (neither from form nor NBS), raise error
        if not srednji_kurs or srednji_kurs <= 0:
            raise ValueError(
                f"NBS kurs nije dostupan za {valuta_fakture} na datum {datum_prometa}. "
                f"Molimo unesite kurs ručno."
            )

        # Foreign currency invoices are always in English
        jezik = 'en'

    # Create faktura instance
    faktura = Faktura(
        firma_id=firma.id,
        komitent_id=data.get('komitent_id'),
        user_id=user.id,
        broj_fakture=broj_fakture,
        tip_fakture=tip_fakture,
        valuta_fakture=valuta_fakture,
        jezik=jezik,  # 'sr' for domestic, 'en' for foreign currency
        datum_prometa=data.get('datum_prometa'),
        valuta_placanja=data.get('valuta_placanja'),
        datum_dospeca=datum_dospeca,
        broj_ugovora=data.get('broj_ugovora'),
        broj_odluke=data.get('broj_odluke'),
        broj_narudzbenice=data.get('broj_narudzbenice'),
        poziv_na_broj=data.get('poziv_na_broj'),
        model=data.get('model'),
        srednji_kurs=srednji_kurs,  # Store NBS exchange rate for foreign currency
        ukupan_iznos_rsd=Decimal('0.00'),  # Will be calculated below
        ukupan_iznos_originalna_valuta=Decimal('0.00'),  # Will be calculated below
        status='draft'
    )

    db.session.add(faktura)
    db.session.flush()  # Get faktura.id

    # Set unique draft number using faktura ID
    faktura.broj_fakture = f"DRAFT-{faktura.id}"

    # Create faktura stavke (line items)
    ukupan_iznos = Decimal('0.00')
    for i, stavka_data in enumerate(data.get('stavke', []), start=1):
        # Calculate ukupno for this stavka
        kolicina = Decimal(str(stavka_data.get('kolicina', 0)))
        cena = Decimal(str(stavka_data.get('cena', 0)))
        ukupno = kolicina * cena

        stavka = FakturaStavka(
            faktura_id=faktura.id,
            artikal_id=stavka_data.get('artikal_id'),
            naziv=stavka_data.get('naziv'),
            kolicina=kolicina,
            jedinica_mere=stavka_data.get('jedinica_mere'),
            cena=cena,
            ukupno=ukupno,
            redni_broj=i
        )
        db.session.add(stavka)
        ukupan_iznos += ukupno

    # Update faktura total amounts
    if valuta_fakture == 'RSD':
        # Domestic invoice - only RSD amount
        faktura.ukupan_iznos_rsd = ukupan_iznos
        faktura.ukupan_iznos_originalna_valuta = None
    else:
        # Foreign currency invoice - calculate both amounts
        faktura.ukupan_iznos_originalna_valuta = ukupan_iznos
        # CODE-001: Use quantize to ensure proper decimal precision (2 decimals for currency)
        faktura.ukupan_iznos_rsd = (ukupan_iznos * srednji_kurs).quantize(Decimal('0.01'))

    db.session.commit()

    return faktura


def increment_brojac_with_year_check(firma, tip_fakture='standardna'):
    """
    Increment invoice counter with automatic year rollover.

    Checks if the current year is different from the year of the last finalized invoice of the same type.
    If it's a new year, resets counter to 1. Otherwise, increments by 1.

    Args:
        firma: PausalnFirma instance
        tip_fakture: str - Type of invoice ('standardna', 'profaktura', 'avansna')

    Business Rules:
        - Counter resets to 1 on January 1st of each year
        - Each invoice type has its own counter
        - Comparison is based on the year of the LAST FINALIZED invoice of the same type
        - Example: Last standardna in 2025 is #984 → First standardna in 2026 is #1

    Note:
        This function does NOT commit - caller must commit
    """
    # Get the last finalized faktura of this type for this firma
    last_faktura = (
        Faktura.query
        .filter_by(firma_id=firma.id, tip_fakture=tip_fakture, status='izdata')
        .order_by(Faktura.finalized_at.desc())
        .first()
    )

    current_year = datetime.now().year

    if last_faktura:
        # Extract year from last finalized invoice
        last_year = last_faktura.finalized_at.year

        if last_year != current_year:
            # New year - reset counter to 1
            if tip_fakture == 'profaktura':
                firma.brojac_profakture = 1
            elif tip_fakture == 'avansna':
                # Priprema za Story 4.3
                firma.brojac_avansne = 1
            else:  # standardna
                firma.brojac_fakture = 1
        else:
            # Same year - increment counter
            if tip_fakture == 'profaktura':
                firma.brojac_profakture += 1
            elif tip_fakture == 'avansna':
                # Priprema za Story 4.3
                firma.brojac_avansne += 1
            else:  # standardna
                firma.brojac_fakture += 1
    else:
        # No previous invoices of this type - this is the first one
        if tip_fakture == 'profaktura':
            if firma.brojac_profakture == 0:
                firma.brojac_profakture = 1
            else:
                firma.brojac_profakture += 1
        elif tip_fakture == 'avansna':
            # Priprema za Story 4.3
            if firma.brojac_avansne == 0:
                firma.brojac_avansne = 1
            else:
                firma.brojac_avansne += 1
        else:  # standardna
            if firma.brojac_fakture == 0:
                firma.brojac_fakture = 1
            else:
                firma.brojac_fakture += 1


def update_faktura(faktura_id, data, user):
    """
    Update an existing draft invoice with new data.

    Args:
        faktura_id: int - ID of the faktura to update
        data: dict - Form data containing updated invoice fields and stavke
        user: User - Current user updating the invoice

    Returns:
        Faktura: Updated faktura instance (status remains 'draft')

    Raises:
        ValueError: If faktura doesn't exist or is not in draft status

    Business Rules:
        - Only draft invoices can be updated (izdate/stornirane are immutable)
        - Broj fakture cannot be changed (remains DRAFT-{id})
        - Existing stavke are deleted and replaced with new ones
        - Total amount is recalculated as sum of all line items
        - Due date is recalculated with weekend adjustment
        - Status remains 'draft' after update
    """
    faktura = db.session.get(Faktura, faktura_id)

    if not faktura:
        raise ValueError(f"Faktura with ID {faktura_id} not found.")

    # SEC-001: Tenant isolation - validate faktura belongs to user's firma
    if faktura.firma_id != user.firma.id:
        raise ValueError("Faktura ne pripada vašoj firmi.")

    # Validation: Only draft invoices can be edited
    if faktura.status != 'draft':
        raise ValueError(
            f"Cannot update faktura with status '{faktura.status}'. "
            f"Only draft invoices can be edited."
        )

    # Determine if this is a foreign currency invoice
    tip_fakture = data.get('tip_fakture', faktura.tip_fakture)

    # Validate devizna fakture MUST have valid foreign currency
    if tip_fakture == 'devizna':
        valuta_fakture = data.get('valuta_fakture')
        if not valuta_fakture or valuta_fakture not in ['EUR', 'USD', 'GBP', 'CHF']:
            raise ValueError(
                "Devizna faktura mora imati valutu (EUR, USD, GBP ili CHF). "
                "Molimo izaberite valutu."
            )
    else:
        valuta_fakture = 'RSD'

    # For foreign currency invoices, fetch NBS exchange rate
    srednji_kurs = None
    jezik = 'sr'  # Default to Serbian

    if tip_fakture == 'devizna':
        # Validate komitent has at least one devizni račun for foreign currency invoices
        from app.models.komitent import Komitent
        komitent = db.session.get(Komitent, data.get('komitent_id'))
        if not komitent:
            raise ValueError("Komitent nije pronađen.")
        # SEC-001: Tenant isolation - validate komitent belongs to user's firma
        if komitent.firma_id != user.firma.id:
            raise ValueError("Komitent ne pripada vašoj firmi.")
        if not komitent.devizni_racuni or len(komitent.devizni_racuni) == 0:
            raise ValueError(
                "Komitent mora imati bar jedan devizni račun za devizne fakture. "
                "Molimo ažurirajte podatke komitenta pre kreiranja devizne fakture."
            )

        datum_prometa = data.get('datum_prometa')

        # Check if manual srednji_kurs is provided in form (user override)
        if data.get('srednji_kurs'):
            srednji_kurs = Decimal(str(data.get('srednji_kurs')))
        else:
            # Fetch from NBS
            srednji_kurs = get_kurs(valuta_fakture, datum_prometa)

        # If no kurs available (neither from form nor NBS), raise error
        if not srednji_kurs or srednji_kurs <= 0:
            raise ValueError(
                f"NBS kurs nije dostupan za {valuta_fakture} na datum {datum_prometa}. "
                f"Molimo unesite kurs ručno."
            )

        # Foreign currency invoices are always in English
        jezik = 'en'

    # Update faktura fields
    faktura.tip_fakture = tip_fakture
    faktura.valuta_fakture = valuta_fakture
    faktura.jezik = jezik
    faktura.komitent_id = data.get('komitent_id')
    faktura.datum_prometa = data.get('datum_prometa')
    faktura.valuta_placanja = data.get('valuta_placanja')
    faktura.broj_ugovora = data.get('broj_ugovora')
    faktura.broj_odluke = data.get('broj_odluke')
    faktura.broj_narudzbenice = data.get('broj_narudzbenice')
    faktura.poziv_na_broj = data.get('poziv_na_broj')
    faktura.model = data.get('model')
    faktura.srednji_kurs = srednji_kurs

    # Recalculate datum_dospeca
    faktura.datum_dospeca = calculate_datum_dospeca(
        data.get('datum_prometa'),
        data.get('valuta_placanja')
    )

    # Delete existing stavke (cascade will handle this)
    db.session.query(FakturaStavka).filter_by(faktura_id=faktura_id).delete()

    # Create new stavke from data
    ukupan_iznos = Decimal('0.00')
    for i, stavka_data in enumerate(data.get('stavke', []), start=1):
        # Calculate ukupno for this stavka
        kolicina = Decimal(str(stavka_data.get('kolicina', 0)))
        cena = Decimal(str(stavka_data.get('cena', 0)))
        ukupno = kolicina * cena

        stavka = FakturaStavka(
            faktura_id=faktura.id,
            artikal_id=stavka_data.get('artikal_id'),
            naziv=stavka_data.get('naziv'),
            kolicina=kolicina,
            jedinica_mere=stavka_data.get('jedinica_mere'),
            cena=cena,
            ukupno=ukupno,
            redni_broj=i
        )
        db.session.add(stavka)
        ukupan_iznos += ukupno

    # Update faktura total amounts
    if valuta_fakture == 'RSD':
        # Domestic invoice - only RSD amount
        faktura.ukupan_iznos_rsd = ukupan_iznos
        faktura.ukupan_iznos_originalna_valuta = None
    else:
        # Foreign currency invoice - calculate both amounts
        faktura.ukupan_iznos_originalna_valuta = ukupan_iznos
        # CODE-001: Use quantize to ensure proper decimal precision (2 decimals for currency)
        faktura.ukupan_iznos_rsd = (ukupan_iznos * srednji_kurs).quantize(Decimal('0.01'))

    # Commit changes
    db.session.commit()

    # Security logging - audit trail for faktura updates
    security_logger.info(
        f"Faktura updated: faktura_id={faktura.id}, broj_fakture={faktura.broj_fakture}, "
        f"tip={faktura.tip_fakture}, komitent_id={faktura.komitent_id}, "
        f"iznos={faktura.ukupan_iznos_rsd}, stavke_count={len(faktura.stavke)}, "
        f"updated_by={user.email}, ip={request.remote_addr if request else 'N/A'}, "
        f"timestamp={datetime.now().isoformat()}"
    )

    return faktura


def finalize_faktura(faktura_id):
    """
    Finalize a draft invoice, making it official and immutable.

    Args:
        faktura_id: int - ID of the faktura to finalize

    Returns:
        Faktura: Finalized faktura instance

    Raises:
        ValueError: If faktura doesn't exist or is not in draft status

    Business Rules:
        - Generates final invoice number from firma's counter
        - Changes status from 'draft' to 'izdata'
        - Increments firma's invoice counter (with year rollover check)
        - Sets finalized_at timestamp
        - Triggers background PDF generation (Celery task)
        - Finalized invoices are immutable (cannot be edited)
    """
    faktura = db.session.get(Faktura, faktura_id)

    if not faktura:
        raise ValueError(f"Faktura with ID {faktura_id} not found.")

    if faktura.status != 'draft':
        raise ValueError(f"Cannot finalize faktura with status '{faktura.status}'. Only draft invoices can be finalized.")

    # Generate final invoice number (replacing DRAFT-{id} with real number)
    faktura.broj_fakture = generate_broj_fakture(faktura.firma, faktura.tip_fakture)

    # Change status to 'izdata' (issued)
    faktura.status = 'izdata'

    # Set finalized timestamp
    faktura.finalized_at = datetime.now()

    # Increment firma's invoice counter (with year rollover check)
    increment_brojac_with_year_check(faktura.firma, faktura.tip_fakture)

    # Set PDF status to 'generating' (Celery task will update to 'generated' or 'failed')
    faktura.status_pdf = 'generating'

    db.session.commit()

    # Trigger background PDF generation (async Celery task)
    from flask import current_app
    try:
        # Lazy import to avoid circular dependency
        import celery_worker
        celery_worker.generate_faktura_pdf_task_async.apply_async(args=[faktura_id])
        current_app.logger.info(f"PDF generation task queued for Faktura {faktura_id}")
    except Exception as e:
        current_app.logger.error(f"Failed to queue PDF task for Faktura {faktura_id}: {e}")
        # Don't fail finalization - user can retry PDF from UI

    return faktura


def list_fakture(user, filters=None, page=1, per_page=20, sort_by='datum_prometa', sort_order='desc'):
    """
    List and filter invoices with pagination and sorting.

    This function implements tenant isolation (pausalac sees only their firma's fakture,
    admin sees all fakture in god mode) and applies filters, search, sorting, and pagination.

    Args:
        user: User - Current user (for tenant isolation)
        filters: dict - Optional filters:
            - datum_od: date - Start date filter
            - datum_do: date - End date filter
            - komitent_id: int - Filter by komitent
            - status: str - Filter by status ('draft', 'izdata', 'stornirana')
            - valuta: str - Filter by currency ('RSD', 'EUR', 'USD', 'GBP', 'CHF')
            - search: str - Search by invoice number (LIKE query)
            - firma_id: int - Admin-only: Filter by specific firma
        page: int - Page number (1-indexed)
        per_page: int - Number of invoices per page (default: 20)
        sort_by: str - Sort column ('broj_fakture', 'datum_prometa', 'ukupan_iznos_rsd')
        sort_order: str - Sort order ('asc' or 'desc')

    Returns:
        Pagination object with .items, .total, .page, .pages, .has_prev, .has_next, etc.

    Business Rules:
        - Pausalac sees only fakture from their firma (automatic filtering)
        - Admin sees all fakture (god mode) unless firma_id filter is provided
        - All filters are optional and can be combined
        - Search by broj_fakture uses LIKE query (case-insensitive)
        - Default sorting: newest first (datum_prometa DESC)
    """
    from app.models.komitent import Komitent
    from app.models.pausaln_firma import PausalnFirma

    if filters is None:
        filters = {}

    # Input validation
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:  # Max limit to prevent memory exhaustion
        per_page = 20  # Default

    # Start with base query
    # Use joinedload for eager loading relationships (komitent, firma)
    from sqlalchemy.orm import joinedload
    query = Faktura.query.options(
        joinedload(Faktura.komitent),
        joinedload(Faktura.firma)
    )

    # Apply tenant isolation (pausalac sees only their firma, admin sees all)
    # Admin can optionally filter by specific firma_id using filters['firma_id']
    if user.role == 'admin' and 'firma_id' in filters and filters['firma_id']:
        # Admin filtering by specific firma
        query = query.filter(Faktura.firma_id == filters['firma_id'])
    elif user.role == 'pausalac':
        # Pausalac sees only their firma's fakture
        query = query.filter(Faktura.firma_id == user.firma_id)
    # else: admin with no firma_id filter = god mode (no filtering)

    # Apply filters
    if filters.get('datum_od'):
        query = query.filter(Faktura.datum_prometa >= filters['datum_od'])

    if filters.get('datum_do'):
        query = query.filter(Faktura.datum_prometa <= filters['datum_do'])

    if filters.get('komitent_id'):
        query = query.filter(Faktura.komitent_id == filters['komitent_id'])

    if filters.get('status'):
        query = query.filter(Faktura.status == filters['status'])

    if filters.get('valuta'):
        query = query.filter(Faktura.valuta_fakture == filters['valuta'])

    if filters.get('tip_fakture'):
        query = query.filter(Faktura.tip_fakture == filters['tip_fakture'])

    # Search by invoice number (case-insensitive LIKE query)
    if filters.get('search'):
        search_term = f"%{filters['search']}%"
        query = query.filter(Faktura.broj_fakture.ilike(search_term))

    # Apply sorting
    valid_sort_columns = {
        'broj_fakture': Faktura.broj_fakture,
        'datum_prometa': Faktura.datum_prometa,
        'ukupan_iznos_rsd': Faktura.ukupan_iznos_rsd
    }

    if sort_by in valid_sort_columns:
        sort_column = valid_sort_columns[sort_by]
        if sort_order == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
    else:
        # Default sort: newest first (datum_prometa DESC)
        query = query.order_by(Faktura.datum_prometa.desc())

    # Apply pagination (error_out=False means don't raise 404 if page is out of range)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return pagination
