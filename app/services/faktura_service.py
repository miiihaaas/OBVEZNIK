"""Business logic for Faktura (Invoice) management."""
from datetime import datetime, timedelta
from decimal import Decimal
from app import db
from app.models.faktura import Faktura
from app.models.faktura_stavka import FakturaStavka
from app.models.pausaln_firma import PausalnFirma


def generate_broj_fakture(firma):
    """
    Generate the next invoice number based on firma's prefix, counter, and suffix.

    Args:
        firma: PausalnFirma instance

    Returns:
        str: Generated invoice number (e.g., "MK-001/2025-PS")

    Note:
        Does NOT increment the counter - that happens only during finalization.
    """
    prefiks = firma.prefiks_fakture or ''
    brojac = str(firma.brojac_fakture).zfill(4)  # Pad with zeros (e.g., 0001)
    sufiks = firma.sufiks_fakture or ''

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
        - Invoice number is generated but counter is NOT incremented yet
        - Due date is calculated with weekend adjustment
        - Total amount is calculated as sum of all line items
    """
    firma = user.firma

    # Generate invoice number (without incrementing counter)
    broj_fakture = generate_broj_fakture(firma)

    # Calculate due date
    datum_dospeca = calculate_datum_dospeca(
        data.get('datum_prometa'),
        data.get('valuta_placanja')
    )

    # Create faktura instance
    faktura = Faktura(
        firma_id=firma.id,
        komitent_id=data.get('komitent_id'),
        user_id=user.id,
        broj_fakture=broj_fakture,
        tip_fakture=data.get('tip_fakture', 'standardna'),
        valuta_fakture='RSD',  # Story 3.1 is only RSD
        jezik='sr',  # Default Serbian
        datum_prometa=data.get('datum_prometa'),
        valuta_placanja=data.get('valuta_placanja'),
        datum_dospeca=datum_dospeca,
        broj_ugovora=data.get('broj_ugovora'),
        broj_odluke=data.get('broj_odluke'),
        broj_narudzbenice=data.get('broj_narudzbenice'),
        poziv_na_broj=data.get('poziv_na_broj'),
        model=data.get('model'),
        ukupan_iznos_rsd=Decimal('0.00'),  # Will be calculated below
        status='draft'
    )

    db.session.add(faktura)
    db.session.flush()  # Get faktura.id

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

    # Update faktura total amount
    faktura.ukupan_iznos_rsd = ukupan_iznos

    db.session.commit()

    return faktura


def increment_brojac_with_year_check(firma):
    """
    Increment invoice counter with automatic year rollover.

    Checks if the current year is different from the year of the last finalized invoice.
    If it's a new year, resets counter to 1. Otherwise, increments by 1.

    Args:
        firma: PausalnFirma instance

    Business Rules:
        - Counter resets to 1 on January 1st of each year
        - Comparison is based on the year of the LAST FINALIZED invoice, not today's date
        - Example: Last invoice in 2025 is #984 → First invoice in 2026 is #1

    Note:
        This function does NOT commit - caller must commit
    """
    # Get the last finalized faktura for this firma
    last_faktura = (
        Faktura.query
        .filter_by(firma_id=firma.id, status='izdata')
        .order_by(Faktura.finalized_at.desc())
        .first()
    )

    current_year = datetime.now().year

    if last_faktura:
        # Extract year from last finalized invoice
        last_year = last_faktura.finalized_at.year

        if last_year != current_year:
            # New year - reset counter to 1
            firma.brojac_fakture = 1
        else:
            # Same year - increment counter
            firma.brojac_fakture += 1
    else:
        # No previous invoices - this is the first one, ensure counter is at least 1
        if firma.brojac_fakture == 0:
            firma.brojac_fakture = 1
        else:
            firma.brojac_fakture += 1


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
        - Changes status from 'draft' to 'izdata'
        - Increments firma's invoice counter (with year rollover check)
        - Sets finalized_at timestamp
        - Finalized invoices are immutable (cannot be edited)
    """
    faktura = db.session.get(Faktura, faktura_id)

    if not faktura:
        raise ValueError(f"Faktura with ID {faktura_id} not found.")

    if faktura.status != 'draft':
        raise ValueError(f"Cannot finalize faktura with status '{faktura.status}'. Only draft invoices can be finalized.")

    # Change status to 'izdata' (issued)
    faktura.status = 'izdata'

    # Set finalized timestamp
    faktura.finalized_at = datetime.now()

    # Increment firma's invoice counter (with year rollover check)
    increment_brojac_with_year_check(faktura.firma)

    db.session.commit()

    return faktura
