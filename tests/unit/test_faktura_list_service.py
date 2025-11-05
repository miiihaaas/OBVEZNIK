"""Unit tests for Faktura List Service (list_fakture function)."""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.komitent import Komitent
from app.models.faktura import Faktura
from app.models.faktura_stavka import FakturaStavka
from app.services.faktura_service import list_fakture


@pytest.fixture
def pausalac_user_with_firma(app):
    """Create a test pausalac user with firma."""
    firma = PausalnFirma(
        pib='12345678',
        maticni_broj='12345678',
        naziv='Test Pausalac Firma',
        adresa='Test Adresa 1',
        broj='1',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        telefon='011111111',
        email='firma@test.com',
        dinarski_racuni=[{'banka': 'Test Banka', 'racun': '123-456789-00'}],
        prefiks_fakture='PF-',
        sufiks_fakture='/2025',
        brojac_fakture=1
    )
    db.session.add(firma)
    db.session.flush()

    user = User(
        email='pausalac@test.com',
        full_name='Test Pausalac',
        role='pausalac',
        firma_id=firma.id
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()

    yield user, firma

    # Release database connection
    db.session.remove()


@pytest.fixture
def admin_user(app):
    """Create a test admin user."""
    admin = User(
        email='admin@test.com',
        full_name='Test Admin',
        role='admin',
        firma_id=None  # Admin has no firma_id
    )
    admin.set_password('password123')
    db.session.add(admin)
    db.session.commit()

    yield admin

    # Release database connection
    db.session.remove()


@pytest.fixture
def second_firma_with_user(app):
    """Create a second firma with user for multi-tenant testing."""
    firma2 = PausalnFirma(
        pib='87654321',
        maticni_broj='87654321',
        naziv='Second Firma',
        adresa='Test Adresa 2',
        broj='2',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        telefon='022222222',
        email='firma2@test.com',
        dinarski_racuni=[{'banka': 'Test Banka', 'racun': '987-654321-00'}],
        prefiks_fakture='SF-',
        sufiks_fakture='/2025',
        brojac_fakture=1
    )
    db.session.add(firma2)
    db.session.flush()

    user2 = User(
        email='pausalac2@test.com',
        full_name='Second Pausalac',
        role='pausalac',
        firma_id=firma2.id
    )
    user2.set_password('password123')
    db.session.add(user2)
    db.session.commit()

    yield user2, firma2

    # Release database connection
    db.session.remove()


@pytest.fixture
def sample_fakture(app, pausalac_user_with_firma, second_firma_with_user):
    """Create 25 sample fakture with various statuses, valute, dates."""
    user1, firma1 = pausalac_user_with_firma
    user2, firma2 = second_firma_with_user

    # Create komitenti for both firme
    komitent1 = Komitent(
        firma_id=firma1.id,
        pib='11111111',
        maticni_broj='11111111',
        naziv='Komitent 1',
        adresa='Adresa 1',
        broj='1',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        email='komitent1@test.com'
    )
    db.session.add(komitent1)

    komitent2 = Komitent(
        firma_id=firma2.id,
        pib='22222222',
        maticni_broj='22222222',
        naziv='Komitent 2',
        adresa='Adresa 2',
        broj='2',
        postanski_broj='11000',
        mesto='Novi Sad',
        drzava='Srbija',
        email='komitent2@test.com'
    )
    db.session.add(komitent2)
    db.session.flush()

    # Create 15 fakture for firma1 (various statuses, currencies, dates)
    today = date.today()
    statuses = ['draft', 'izdata', 'stornirana']
    currencies = ['RSD', 'EUR', 'USD']

    for i in range(15):
        faktura = Faktura(
            firma_id=firma1.id,
            komitent_id=komitent1.id,
            user_id=user1.id,
            broj_fakture=f'PF-{i+1:04d}/2025',
            tip_fakture='standardna',
            valuta_fakture=currencies[i % 3],
            datum_prometa=today - timedelta(days=i),
            valuta_placanja=7,
            datum_dospeca=today - timedelta(days=i) + timedelta(days=7),
            ukupan_iznos_rsd=Decimal(f'{(i+1)*1000}.00'),
            status=statuses[i % 3]
        )
        db.session.add(faktura)

    # Create 10 fakture for firma2
    for i in range(10):
        faktura = Faktura(
            firma_id=firma2.id,
            komitent_id=komitent2.id,
            user_id=user2.id,
            broj_fakture=f'SF-{i+1:04d}/2025',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=today - timedelta(days=i),
            valuta_placanja=7,
            datum_dospeca=today - timedelta(days=i) + timedelta(days=7),
            ukupan_iznos_rsd=Decimal(f'{(i+1)*500}.00'),
            status='izdata'
        )
        db.session.add(faktura)

    db.session.commit()

    yield user1, user2, firma1, firma2

    # Release database connection
    db.session.remove()


class TestListFaktureTenantIsolation:
    """Tests for tenant isolation in list_fakture function."""

    def test_pausalac_sees_only_own_fakture(self, app, sample_fakture):
        """Test that pausalac user sees only their firma's fakture."""
        user1, user2, firma1, firma2 = sample_fakture

        # Pausalac 1 should see only firma1 fakture (15 total)
        pagination = list_fakture(user1, filters={}, page=1, per_page=20)

        assert pagination.total == 15
        # Verify all fakture belong to firma1
        for faktura in pagination.items:
            assert faktura.firma_id == firma1.id

    def test_admin_sees_all_fakture(self, app, sample_fakture, admin_user):
        """Test that admin user sees all fakture (god mode)."""
        user1, user2, firma1, firma2 = sample_fakture

        # Admin should see all fakture (15 + 10 = 25 total)
        pagination = list_fakture(admin_user, filters={}, page=1, per_page=30)

        assert pagination.total == 25


class TestListFaktureFiltering:
    """Tests for filtering functionality."""

    def test_filter_by_status_draft(self, app, sample_fakture):
        """Test filtering by status='draft'."""
        user1, user2, firma1, firma2 = sample_fakture

        # Firma1 has 15 fakture, every 3rd is 'draft' (positions 0, 3, 6, 9, 12 = 5 fakture)
        filters = {'status': 'draft'}
        pagination = list_fakture(user1, filters=filters, page=1, per_page=20)

        assert pagination.total == 5
        for faktura in pagination.items:
            assert faktura.status == 'draft'

    def test_filter_by_status_izdata(self, app, sample_fakture):
        """Test filtering by status='izdata'."""
        user1, user2, firma1, firma2 = sample_fakture

        # Firma1 has 15 fakture, every 3rd+1 is 'izdata' (positions 1, 4, 7, 10, 13 = 5 fakture)
        filters = {'status': 'izdata'}
        pagination = list_fakture(user1, filters=filters, page=1, per_page=20)

        assert pagination.total == 5
        for faktura in pagination.items:
            assert faktura.status == 'izdata'

    def test_filter_by_valuta_rsd(self, app, sample_fakture):
        """Test filtering by valuta='RSD'."""
        user1, user2, firma1, firma2 = sample_fakture

        # Firma1 has 15 fakture, every 3rd is 'RSD' (positions 0, 3, 6, 9, 12 = 5 fakture)
        filters = {'valuta': 'RSD'}
        pagination = list_fakture(user1, filters=filters, page=1, per_page=20)

        assert pagination.total == 5
        for faktura in pagination.items:
            assert faktura.valuta_fakture == 'RSD'

    def test_filter_by_date_range(self, app, sample_fakture):
        """Test filtering by date range."""
        user1, user2, firma1, firma2 = sample_fakture

        today = date.today()
        # Filter fakture from last 5 days
        filters = {
            'datum_od': today - timedelta(days=5),
            'datum_do': today
        }
        pagination = list_fakture(user1, filters=filters, page=1, per_page=20)

        # Should have 6 fakture (days 0-5)
        assert pagination.total == 6
        for faktura in pagination.items:
            assert filters['datum_od'] <= faktura.datum_prometa <= filters['datum_do']

    def test_filter_by_komitent(self, app, sample_fakture):
        """Test filtering by komitent_id."""
        user1, user2, firma1, firma2 = sample_fakture

        # Get komitent1 ID
        from app.models.komitent import Komitent
        komitent1 = Komitent.query.filter_by(firma_id=firma1.id).first()

        filters = {'komitent_id': komitent1.id}
        pagination = list_fakture(user1, filters=filters, page=1, per_page=20)

        # All firma1 fakture belong to komitent1
        assert pagination.total == 15
        for faktura in pagination.items:
            assert faktura.komitent_id == komitent1.id

    def test_search_by_broj_fakture(self, app, sample_fakture):
        """Test search by invoice number (LIKE query)."""
        user1, user2, firma1, firma2 = sample_fakture

        # Search for 'PF-0001' or 'PF-0010' (should match 2 fakture: 0001, 0010)
        filters = {'search': 'PF-000'}
        pagination = list_fakture(user1, filters=filters, page=1, per_page=20)

        # Should match PF-0001 through PF-0009 (9 fakture)
        assert pagination.total == 9
        for faktura in pagination.items:
            assert 'PF-000' in faktura.broj_fakture


class TestListFaktureSorting:
    """Tests for sorting functionality."""

    def test_sort_by_datum_prometa_desc(self, app, sample_fakture):
        """Test sorting by datum_prometa descending (newest first)."""
        user1, user2, firma1, firma2 = sample_fakture

        pagination = list_fakture(user1, filters={}, page=1, per_page=20, sort_by='datum_prometa', sort_order='desc')

        # First faktura should have the most recent date
        assert pagination.items[0].datum_prometa == date.today()

    def test_sort_by_datum_prometa_asc(self, app, sample_fakture):
        """Test sorting by datum_prometa ascending (oldest first)."""
        user1, user2, firma1, firma2 = sample_fakture

        pagination = list_fakture(user1, filters={}, page=1, per_page=20, sort_by='datum_prometa', sort_order='asc')

        # First faktura should have the oldest date
        assert pagination.items[0].datum_prometa == date.today() - timedelta(days=14)

    def test_sort_by_ukupan_iznos_desc(self, app, sample_fakture):
        """Test sorting by ukupan_iznos_rsd descending (highest first)."""
        user1, user2, firma1, firma2 = sample_fakture

        pagination = list_fakture(user1, filters={}, page=1, per_page=20, sort_by='ukupan_iznos_rsd', sort_order='desc')

        # First faktura should have the highest amount
        assert pagination.items[0].ukupan_iznos_rsd == Decimal('15000.00')

    def test_sort_by_ukupan_iznos_asc(self, app, sample_fakture):
        """Test sorting by ukupan_iznos_rsd ascending (lowest first)."""
        user1, user2, firma1, firma2 = sample_fakture

        pagination = list_fakture(user1, filters={}, page=1, per_page=20, sort_by='ukupan_iznos_rsd', sort_order='asc')

        # First faktura should have the lowest amount
        assert pagination.items[0].ukupan_iznos_rsd == Decimal('1000.00')

    def test_sort_by_broj_fakture_asc(self, app, sample_fakture):
        """Test sorting by broj_fakture ascending."""
        user1, user2, firma1, firma2 = sample_fakture

        pagination = list_fakture(user1, filters={}, page=1, per_page=20, sort_by='broj_fakture', sort_order='asc')

        # First should be PF-0001/2025 (lexicographically smallest)
        assert pagination.items[0].broj_fakture == 'PF-0001/2025'
        # Last should be PF-0015/2025 (lexicographically largest)
        assert pagination.items[-1].broj_fakture == 'PF-0015/2025'

    def test_sort_by_broj_fakture_desc(self, app, sample_fakture):
        """Test sorting by broj_fakture descending."""
        user1, user2, firma1, firma2 = sample_fakture

        pagination = list_fakture(user1, filters={}, page=1, per_page=20, sort_by='broj_fakture', sort_order='desc')

        # First should be PF-0015/2025 (lexicographically largest)
        assert pagination.items[0].broj_fakture == 'PF-0015/2025'
        # Last should be PF-0001/2025 (lexicographically smallest)
        assert pagination.items[-1].broj_fakture == 'PF-0001/2025'


class TestListFakturePagination:
    """Tests for pagination functionality."""

    def test_pagination_first_page(self, app, sample_fakture):
        """Test pagination on first page (20 per page)."""
        user1, user2, firma1, firma2 = sample_fakture

        pagination = list_fakture(user1, filters={}, page=1, per_page=20)

        assert pagination.page == 1
        assert pagination.per_page == 20
        assert pagination.total == 15
        assert len(pagination.items) == 15  # Only 15 fakture, all on first page
        assert pagination.pages == 1
        assert not pagination.has_prev
        assert not pagination.has_next

    def test_pagination_with_10_per_page(self, app, sample_fakture):
        """Test pagination with 10 items per page (15 fakture = 2 pages)."""
        user1, user2, firma1, firma2 = sample_fakture

        # Page 1
        pagination = list_fakture(user1, filters={}, page=1, per_page=10)

        assert pagination.page == 1
        assert pagination.pages == 2
        assert len(pagination.items) == 10
        assert not pagination.has_prev
        assert pagination.has_next

        # Page 2
        pagination = list_fakture(user1, filters={}, page=2, per_page=10)

        assert pagination.page == 2
        assert len(pagination.items) == 5  # Remaining 5 fakture
        assert pagination.has_prev
        assert not pagination.has_next


class TestCombinedFilters:
    """Tests for combining multiple filters."""

    def test_combined_status_and_valuta(self, app, sample_fakture):
        """Test combining status and valuta filters."""
        user1, user2, firma1, firma2 = sample_fakture

        # Filter: status='izdata' AND valuta='EUR'
        # Pattern: i%3 -> currencies[RSD,EUR,USD], statuses[draft,izdata,stornirana]
        # Positions 1,4,7,10,13 have status='izdata' AND valuta='EUR' (5 fakture)
        filters = {'status': 'izdata', 'valuta': 'EUR'}
        pagination = list_fakture(user1, filters=filters, page=1, per_page=20)

        assert pagination.total == 5
        for faktura in pagination.items:
            assert faktura.status == 'izdata'
            assert faktura.valuta_fakture == 'EUR'
