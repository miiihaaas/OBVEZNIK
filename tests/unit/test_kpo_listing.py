"""Unit tests for KPO listing service layer."""
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from app import db
from app.models.kpo_entry import KPOEntry
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.komitent import Komitent
from app.models.faktura import Faktura
from app.services.kpo_service import (
    list_kpo_entries,
    get_kpo_entries_list,
    calculate_total_promet_with_filters
)


@pytest.fixture
def pausalac_user(clean_database):
    """Create a test pausalac user with firma."""
    firma = PausalnFirma(
        pib='12345678',
        maticni_broj='87654321',
        naziv='Test Firma',
        adresa='Test adresa 1',
        broj='1',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        telefon='0112345678',
        email='test@firma.rs',
        dinarski_racuni='{"racun": "160-123456-78"}',
        prefiks_fakture='TF',
        sufiks_fakture='PS'
    )
    db.session.add(firma)
    db.session.flush()

    user = User(
        email='pausalac@test.com',
        full_name='Test Paušalac',
        role='pausalac',
        firma_id=firma.id
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()

    return user


@pytest.fixture
def admin_user(clean_database):
    """Create a test admin user."""
    user = User(
        email='admin@test.com',
        full_name='Test Admin',
        role='admin'
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()

    return user


@pytest.fixture
def sample_kpo_entries(clean_database, pausalac_user):
    """Create sample KPO entries for testing."""
    entries = []
    fakture = []

    # Create 5 "izdata" entries
    for i in range(1, 6):
        # Create Komitent
        komitent = Komitent(
            firma_id=pausalac_user.firma_id,
            pib=f'1234567{i}',
            maticni_broj=f'8765432{i}',
            naziv=f'Komitent {i}',
            adresa='Test adresa',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            email=f'komitent{i}@test.rs'
        )
        db.session.add(komitent)
        db.session.flush()

        # Create Faktura
        faktura = Faktura(
            firma_id=pausalac_user.firma_id,
            komitent_id=komitent.id,
            user_id=pausalac_user.id,
            broj_fakture=f'TF-{i:03d}/2025-PS',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            jezik='sr',
            datum_prometa=date(2025, 1, i),
            valuta_placanja=15,
            datum_dospeca=date(2025, 1, i + 15),
            ukupan_iznos_rsd=Decimal('1000.00') * i,
            status='izdata'
        )
        db.session.add(faktura)
        db.session.flush()
        fakture.append(faktura)

        # Create KPO entry
        entry = KPOEntry(
            firma_id=pausalac_user.firma_id,
            faktura_id=faktura.id,
            redni_broj=i,
            broj_fakture=f'TF-{i:03d}/2025-PS',
            datum_prometa=date(2025, 1, i),
            datum_dospeca=date(2025, 1, i + 15),
            komitent_naziv=f'Komitent {i}',
            komitent_pib=f'1234567{i}',
            opis=f'Test opis {i}',
            iznos_rsd=Decimal('1000.00') * i,
            valuta='RSD',
            status_fakture='izdata',
            godina=2025
        )
        db.session.add(entry)
        entries.append(entry)

    # Create 2 "stornirana" entries
    for i in range(6, 8):
        # Create Komitent
        komitent = Komitent(
            firma_id=pausalac_user.firma_id,
            pib=f'1234567{i}',
            maticni_broj=f'8765432{i}',
            naziv=f'Komitent {i}',
            adresa='Test adresa',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            email=f'komitent{i}@test.rs'
        )
        db.session.add(komitent)
        db.session.flush()

        # Create Faktura
        faktura = Faktura(
            firma_id=pausalac_user.firma_id,
            komitent_id=komitent.id,
            user_id=pausalac_user.id,
            broj_fakture=f'TF-{i:03d}/2025-PS',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            jezik='sr',
            datum_prometa=date(2025, 1, i),
            valuta_placanja=15,
            datum_dospeca=date(2025, 1, i + 15),
            ukupan_iznos_rsd=Decimal('500.00'),
            status='stornirana'
        )
        db.session.add(faktura)
        db.session.flush()
        fakture.append(faktura)

        # Create KPO entry
        entry = KPOEntry(
            firma_id=pausalac_user.firma_id,
            faktura_id=faktura.id,
            redni_broj=i,
            broj_fakture=f'TF-{i:03d}/2025-PS',
            datum_prometa=date(2025, 1, i),
            datum_dospeca=date(2025, 1, i + 15),
            komitent_naziv=f'Komitent {i}',
            komitent_pib=f'1234567{i}',
            opis=f'Test opis {i}',
            iznos_rsd=Decimal('500.00'),
            valuta='RSD',
            status_fakture='stornirana',
            godina=2025
        )
        db.session.add(entry)
        entries.append(entry)

    db.session.commit()

    return entries


def test_list_kpo_entries_pausalac_sees_only_own_firma(clean_database, pausalac_user, sample_kpo_entries):
    """Test tenant isolation: pausalac sees only own firma entries."""
    filters = {'godina': 2025, 'status_filter': 'all'}
    pagination = list_kpo_entries(
        user=pausalac_user,
        filters=filters,
        page=1,
        per_page=20,
        sort_by='redni_broj',
        sort_order='asc'
    )

    assert pagination.total == 7  # 5 izdata + 2 stornirana
    assert all(entry.firma_id == pausalac_user.firma_id for entry in pagination.items)


def test_list_kpo_entries_filter_by_status_izdata_only(clean_database, pausalac_user, sample_kpo_entries):
    """Test default filter: only 'izdata' entries."""
    filters = {'godina': 2025, 'status_filter': 'izdata'}
    pagination = list_kpo_entries(
        user=pausalac_user,
        filters=filters,
        page=1,
        per_page=20
    )

    assert pagination.total == 5  # Only izdata entries
    assert all(entry.status_fakture == 'izdata' for entry in pagination.items)


def test_list_kpo_entries_sort_by_datum_prometa_desc(clean_database, pausalac_user, sample_kpo_entries):
    """Test default sort: datum_prometa DESC."""
    filters = {'godina': 2025}
    pagination = list_kpo_entries(
        user=pausalac_user,
        filters=filters,
        page=1,
        per_page=20,
        sort_by='datum_prometa',
        sort_order='desc'
    )

    items = pagination.items
    assert len(items) > 0
    # Check descending order
    for i in range(len(items) - 1):
        assert items[i].datum_prometa >= items[i + 1].datum_prometa


def test_calculate_total_promet_excludes_stornirane(clean_database, pausalac_user, sample_kpo_entries):
    """Test total promet excludes stornirane fakture (AC: 5)."""
    filters = {'godina': 2025, 'status_filter': 'izdata'}
    total = calculate_total_promet_with_filters(
        user=pausalac_user,
        filters=filters
    )

    # Sum of izdata entries: 1000 + 2000 + 3000 + 4000 + 5000 = 15000
    expected_total = Decimal('15000.00')
    assert total == expected_total


def test_kpo_entries_pagination_works(clean_database, pausalac_user, sample_kpo_entries):
    """Test pagination logic (AC: 8)."""
    filters = {'godina': 2025, 'status_filter': 'all'}
    pagination = list_kpo_entries(
        user=pausalac_user,
        filters=filters,
        page=1,
        per_page=3,  # Small page size for testing
        sort_by='redni_broj',
        sort_order='asc'
    )

    assert pagination.total == 7
    assert len(pagination.items) == 3
    assert pagination.pages == 3
    assert pagination.has_next is True
    assert pagination.has_prev is False

    # Check second page
    pagination_page2 = list_kpo_entries(
        user=pausalac_user,
        filters=filters,
        page=2,
        per_page=3
    )

    assert len(pagination_page2.items) == 3
    assert pagination_page2.has_next is True
    assert pagination_page2.has_prev is True


def test_list_kpo_entries_filter_by_datum_range(clean_database, pausalac_user, sample_kpo_entries):
    """Test filter by datum_od and datum_do (AC: 3)."""
    filters = {
        'godina': 2025,
        'datum_od': date(2025, 1, 3),
        'datum_do': date(2025, 1, 5)
    }
    pagination = list_kpo_entries(
        user=pausalac_user,
        filters=filters,
        page=1,
        per_page=20
    )

    # Entries with datum_prometa between 3rd and 5th
    assert pagination.total == 3  # Entries 3, 4, 5
    for entry in pagination.items:
        assert filters['datum_od'] <= entry.datum_prometa <= filters['datum_do']


def test_get_kpo_entries_list_no_pagination(clean_database, pausalac_user, sample_kpo_entries):
    """Test get_kpo_entries_list returns all entries without pagination."""
    filters = {'godina': 2025, 'status_filter': 'all'}
    entries = get_kpo_entries_list(
        user=pausalac_user,
        filters=filters,
        sort_by='redni_broj',
        sort_order='asc'
    )

    assert len(entries) == 7  # All entries
    assert isinstance(entries, list)
