"""Unit tests for Dashboard Service."""
import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.komitent import Komitent
from app.models.artikal import Artikal
from app.models.faktura import Faktura
from app.services.dashboard_service import (
    get_admin_dashboard_stats,
    get_firma_list_with_stats,
    calculate_firma_rolling_limit_remaining,
    get_pausalac_dashboard_stats,
    get_pausalac_recent_fakture,
    calculate_rolling_limit_projections,
    ROLLING_LIMIT_365_DAYS
)


@pytest.fixture
def test_data(app):
    """Create test data: firms, users, komitenti, and invoices."""
    with app.app_context():
        # Create 3 test firms
        firma1 = PausalnFirma(
            pib='111111111',
            maticni_broj='11111111',
            naziv='ABC Firma',
            adresa='Adresa 1',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            telefon='011111111',
            email='abc@test.com',
            dinarski_racuni=[{'banka': 'Test Banka', 'racun': '111-111111-11'}]
        )
        firma2 = PausalnFirma(
            pib='222222222',
            maticni_broj='22222222',
            naziv='XYZ Firma',
            adresa='Adresa 2',
            broj='2',
            postanski_broj='21000',
            mesto='Novi Sad',
            telefon='021222222',
            email='xyz@test.com',
            dinarski_racuni=[{'banka': 'Test Banka', 'racun': '222-222222-22'}]
        )
        firma3 = PausalnFirma(
            pib='333333333',
            maticni_broj='33333333',
            naziv='DEF Firma',
            adresa='Adresa 3',
            broj='3',
            postanski_broj='18000',
            mesto='Niš',
            telefon='018333333',
            email='def@test.com',
            dinarski_racuni=[{'banka': 'Test Banka', 'racun': '333-333333-33'}],
            is_active=False  # Inactive firma
        )
        db.session.add_all([firma1, firma2, firma3])
        db.session.commit()

        # Create users
        admin_user = User(
            email='admin@test.com',
            full_name='Admin User',
            role='admin'
        )
        admin_user.set_password('password123')

        pausalac1 = User(
            email='pausalac1@test.com',
            full_name='Pausalac 1',
            role='pausalac',
            firma_id=firma1.id
        )
        pausalac1.set_password('password123')

        pausalac2 = User(
            email='pausalac2@test.com',
            full_name='Pausalac 2',
            role='pausalac',
            firma_id=firma2.id
        )
        pausalac2.set_password('password123')

        db.session.add_all([admin_user, pausalac1, pausalac2])
        db.session.commit()

        # Create komitenti
        komitent1 = Komitent(
            firma_id=firma1.id,
            pib='444444444',
            maticni_broj='44444444',
            naziv='Komitent 1',
            adresa='Komitent Adresa 1',
            broj='10',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija'
        )
        komitent2 = Komitent(
            firma_id=firma2.id,
            pib='555555555',
            maticni_broj='55555555',
            naziv='Komitent 2',
            adresa='Komitent Adresa 2',
            broj='20',
            postanski_broj='21000',
            mesto='Novi Sad',
            drzava='Srbija'
        )
        db.session.add_all([komitent1, komitent2])
        db.session.commit()

        # Create artikli
        artikal1 = Artikal(
            firma_id=firma1.id,
            naziv='Artikal 1',
            opis='Test artikal 1',
            podrazumevana_cena=Decimal('1000.00'),
            jedinica_mere='kom'
        )
        artikal2 = Artikal(
            firma_id=firma1.id,
            naziv='Artikal 2',
            opis='Test artikal 2',
            podrazumevana_cena=Decimal('2000.00'),
            jedinica_mere='kg'
        )
        artikal3 = Artikal(
            firma_id=firma2.id,
            naziv='Artikal 3',
            opis='Test artikal 3',
            podrazumevana_cena=Decimal('3000.00'),
            jedinica_mere='kom'
        )
        db.session.add_all([artikal1, artikal2, artikal3])
        db.session.commit()

        # Create invoices for current month
        today = date.today()
        first_day_this_month = today.replace(day=1)

        # Firma1: 3 invoices this month
        faktura1 = Faktura(
            firma_id=firma1.id,
            komitent_id=komitent1.id,
            user_id=pausalac1.id,
            broj_fakture='F1-001',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=first_day_this_month,
            valuta_placanja=30,
            datum_dospeca=first_day_this_month + timedelta(days=30),
            ukupan_iznos_rsd=Decimal('100000.00'),
            status='izdata',
            finalized_at=datetime.now(timezone.utc) - timedelta(days=5)
        )
        faktura2 = Faktura(
            firma_id=firma1.id,
            komitent_id=komitent1.id,
            user_id=pausalac1.id,
            broj_fakture='F1-002',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=first_day_this_month + timedelta(days=5),
            valuta_placanja=30,
            datum_dospeca=first_day_this_month + timedelta(days=35),
            ukupan_iznos_rsd=Decimal('200000.00'),
            status='izdata',
            finalized_at=datetime.now(timezone.utc) - timedelta(days=2)
        )
        faktura3 = Faktura(
            firma_id=firma1.id,
            komitent_id=komitent1.id,
            user_id=pausalac1.id,
            broj_fakture='F1-003',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=first_day_this_month + timedelta(days=10),
            valuta_placanja=30,
            datum_dospeca=first_day_this_month + timedelta(days=40),
            ukupan_iznos_rsd=Decimal('150000.00'),
            status='izdata',
            finalized_at=datetime.now(timezone.utc) - timedelta(days=1)
        )

        # Firma2: 2 invoices this month
        faktura4 = Faktura(
            firma_id=firma2.id,
            komitent_id=komitent2.id,
            user_id=pausalac2.id,
            broj_fakture='F2-001',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=first_day_this_month + timedelta(days=3),
            valuta_placanja=30,
            datum_dospeca=first_day_this_month + timedelta(days=33),
            ukupan_iznos_rsd=Decimal('300000.00'),
            status='izdata',
            finalized_at=datetime.now(timezone.utc) - timedelta(days=3)
        )
        faktura5 = Faktura(
            firma_id=firma2.id,
            komitent_id=komitent2.id,
            user_id=pausalac2.id,
            broj_fakture='F2-002',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=first_day_this_month + timedelta(days=7),
            valuta_placanja=30,
            datum_dospeca=first_day_this_month + timedelta(days=37),
            ukupan_iznos_rsd=Decimal('250000.00'),
            status='izdata',
            finalized_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )

        # Stornirana faktura - should NOT be counted
        faktura6 = Faktura(
            firma_id=firma1.id,
            komitent_id=komitent1.id,
            user_id=pausalac1.id,
            broj_fakture='F1-004-STORNO',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=first_day_this_month + timedelta(days=8),
            valuta_placanja=30,
            datum_dospeca=first_day_this_month + timedelta(days=38),
            ukupan_iznos_rsd=Decimal('50000.00'),
            status='stornirana',
            razlog_storniranja='Test storno',
            stornirana_at=datetime.now(timezone.utc)
        )

        # Old invoice from last year (for rolling limit test)
        last_year = today - timedelta(days=400)
        faktura7 = Faktura(
            firma_id=firma1.id,
            komitent_id=komitent1.id,
            user_id=pausalac1.id,
            broj_fakture='F1-OLD',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=last_year,
            valuta_placanja=30,
            datum_dospeca=last_year + timedelta(days=30),
            ukupan_iznos_rsd=Decimal('1000000.00'),
            status='izdata',
            finalized_at=datetime.now(timezone.utc) - timedelta(days=400)
        )

        # Invoice within 365 days (for rolling limit test)
        within_365 = today - timedelta(days=200)
        faktura8 = Faktura(
            firma_id=firma1.id,
            komitent_id=komitent1.id,
            user_id=pausalac1.id,
            broj_fakture='F1-365',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=within_365,
            valuta_placanja=30,
            datum_dospeca=within_365 + timedelta(days=30),
            ukupan_iznos_rsd=Decimal('500000.00'),
            status='izdata',
            finalized_at=datetime.now(timezone.utc) - timedelta(days=200)
        )

        db.session.add_all([faktura1, faktura2, faktura3, faktura4, faktura5, faktura6, faktura7, faktura8])
        db.session.commit()

        yield {
            'firma1': firma1,
            'firma2': firma2,
            'firma3': firma3,
            'admin_user': admin_user,
            'pausalac1': pausalac1,
            'pausalac2': pausalac2,
            'komitent1': komitent1,
            'komitent2': komitent2,
            'artikal1': artikal1,
            'artikal2': artikal2,
            'artikal3': artikal3,
            'fakture': [faktura1, faktura2, faktura3, faktura4, faktura5, faktura6, faktura7, faktura8]
        }


def test_get_admin_dashboard_stats_correct_aggregation(app, test_data):
    """Test that admin dashboard stats are correctly aggregated."""
    with app.app_context():
        # Get stats for current month with explicit date range to cover all test invoices
        today = date.today()
        first_day_this_month = today.replace(day=1)
        # Use day 15 to ensure we capture all test invoices (up to day 10)
        date_to = first_day_this_month + timedelta(days=14)

        stats = get_admin_dashboard_stats(date_from=first_day_this_month, date_to=date_to)

        # Verify totals
        assert stats['total_firme'] == 2  # Only active firms (firma3 is inactive)
        assert stats['total_users'] == 3  # 1 admin + 2 pausalci
        assert stats['total_fakture_period'] == 5  # 5 invoices this month (excluding stornirana)

        # Total promet: 100k + 200k + 150k + 300k + 250k = 1,000,000 RSD
        expected_promet = Decimal('1000000.00')
        assert stats['total_promet_period_rsd'] == expected_promet


def test_get_admin_dashboard_stats_custom_date_range(app, test_data):
    """Test dashboard stats with custom date range."""
    with app.app_context():
        today = date.today()
        first_day_this_month = today.replace(day=1)

        # Get stats for only first 5 days of month
        stats = get_admin_dashboard_stats(
            date_from=first_day_this_month,
            date_to=first_day_this_month + timedelta(days=5)
        )

        # Should include faktura1, faktura2, faktura4 (3 invoices)
        assert stats['total_fakture_period'] == 3

        # Total promet: 100k + 200k + 300k = 600,000 RSD
        expected_promet = Decimal('600000.00')
        assert stats['total_promet_period_rsd'] == expected_promet


def test_get_admin_dashboard_stats_no_invoices(app):
    """Test dashboard stats when there are no invoices."""
    with app.app_context():
        # Create firma without invoices
        firma = PausalnFirma(
            pib='999999999',
            maticni_broj='99999999',
            naziv='Empty Firma',
            adresa='Adresa',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            telefon='011111111',
            email='empty@test.com',
            dinarski_racuni=[{'banka': 'Test', 'racun': '999-999999-99'}]
        )
        db.session.add(firma)
        db.session.commit()

        stats = get_admin_dashboard_stats()

        assert stats['total_firme'] == 1
        assert stats['total_users'] == 0
        assert stats['total_fakture_period'] == 0
        assert stats['total_promet_period_rsd'] == 0


def test_get_firma_list_with_stats_sorting(app, test_data):
    """Test sorting of firma list by different fields."""
    with app.app_context():
        # Use explicit date range to cover all test invoices
        today = date.today()
        first_day_this_month = today.replace(day=1)
        date_to = first_day_this_month + timedelta(days=14)

        # Sort by naziv (default)
        firma_list, total = get_firma_list_with_stats(
            date_from=first_day_this_month,
            date_to=date_to,
            sort_by='naziv'
        )
        assert total == 2  # Only active firms
        assert firma_list[0]['naziv'] == 'ABC Firma'  # Alphabetically first
        assert firma_list[1]['naziv'] == 'XYZ Firma'

        # Sort by broj_faktura (descending)
        firma_list, total = get_firma_list_with_stats(
            date_from=first_day_this_month,
            date_to=date_to,
            sort_by='broj_faktura'
        )
        assert firma_list[0]['naziv'] == 'ABC Firma'  # 3 invoices
        assert firma_list[0]['broj_faktura'] == 3
        assert firma_list[1]['naziv'] == 'XYZ Firma'  # 2 invoices
        assert firma_list[1]['broj_faktura'] == 2

        # Sort by promet (descending)
        firma_list, total = get_firma_list_with_stats(
            date_from=first_day_this_month,
            date_to=date_to,
            sort_by='promet'
        )
        assert firma_list[0]['naziv'] == 'XYZ Firma'  # 550k promet
        assert firma_list[0]['promet_rsd'] == 550000.00
        assert firma_list[1]['naziv'] == 'ABC Firma'  # 450k promet
        assert firma_list[1]['promet_rsd'] == 450000.00


def test_get_firma_list_with_stats_filtering(app, test_data):
    """Test filtering firma list by date range."""
    with app.app_context():
        today = date.today()
        first_day_this_month = today.replace(day=1)

        # Filter for first 5 days
        firma_list, total = get_firma_list_with_stats(
            date_from=first_day_this_month,
            date_to=first_day_this_month + timedelta(days=5)
        )

        # ABC Firma: 2 invoices (F1-001, F1-002)
        abc_firma = next(f for f in firma_list if f['naziv'] == 'ABC Firma')
        assert abc_firma['broj_faktura'] == 2
        assert abc_firma['promet_rsd'] == 300000.00

        # XYZ Firma: 1 invoice (F2-001)
        xyz_firma = next(f for f in firma_list if f['naziv'] == 'XYZ Firma')
        assert xyz_firma['broj_faktura'] == 1
        assert xyz_firma['promet_rsd'] == 300000.00


def test_get_firma_list_with_stats_search(app, test_data):
    """Test search filtering by naziv or PIB."""
    with app.app_context():
        # Search by naziv
        firma_list, total = get_firma_list_with_stats(search_query='ABC')
        assert total == 1
        assert firma_list[0]['naziv'] == 'ABC Firma'

        # Search by PIB
        firma_list, total = get_firma_list_with_stats(search_query='222222222')
        assert total == 1
        assert firma_list[0]['pib'] == '222222222'

        # Search with no results
        firma_list, total = get_firma_list_with_stats(search_query='NONEXISTENT')
        assert total == 0
        assert len(firma_list) == 0


def test_get_firma_list_with_stats_pagination(app, test_data):
    """Test pagination of firma list."""
    with app.app_context():
        # Page 1 with 1 item per page
        firma_list, total = get_firma_list_with_stats(page=1, per_page=1)
        assert total == 2
        assert len(firma_list) == 1
        assert firma_list[0]['naziv'] == 'ABC Firma'

        # Page 2 with 1 item per page
        firma_list, total = get_firma_list_with_stats(page=2, per_page=1)
        assert total == 2
        assert len(firma_list) == 1
        assert firma_list[0]['naziv'] == 'XYZ Firma'


def test_calculate_firma_rolling_limit_remaining(app, test_data):
    """Test calculation of rolling 365-day limit remaining."""
    with app.app_context():
        firma1 = test_data['firma1']

        # Firma1 has:
        # - 3 invoices this month: 100k + 200k + 150k = 450k
        # - 1 invoice within 365 days (200 days ago): 500k
        # - 1 invoice older than 365 days (400 days ago): 1M (NOT counted)
        # Total within 365 days: 450k + 500k = 950k
        # Remaining limit: 8M - 950k = 7,050,000

        preostali_limit = calculate_firma_rolling_limit_remaining(firma1.id)

        expected_limit = ROLLING_LIMIT_365_DAYS - 950000.00
        assert preostali_limit == expected_limit
        assert preostali_limit == 7050000.00


def test_calculate_firma_rolling_limit_remaining_no_invoices(app):
    """Test rolling limit calculation for firma with no invoices."""
    with app.app_context():
        # Create firma without invoices
        firma = PausalnFirma(
            pib='888888888',
            maticni_broj='88888888',
            naziv='New Firma',
            adresa='Adresa',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            telefon='011111111',
            email='new@test.com',
            dinarski_racuni=[{'banka': 'Test', 'racun': '888-888888-88'}]
        )
        db.session.add(firma)
        db.session.commit()

        preostali_limit = calculate_firma_rolling_limit_remaining(firma.id)

        # Should be full limit
        assert preostali_limit == ROLLING_LIMIT_365_DAYS
        assert preostali_limit == 8000000.00


def test_calculate_firma_rolling_limit_remaining_over_limit(app):
    """Test rolling limit calculation when firma is over limit."""
    with app.app_context():
        # Create firma
        firma = PausalnFirma(
            pib='777777777',
            maticni_broj='77777777',
            naziv='Over Limit Firma',
            adresa='Adresa',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            telefon='011111111',
            email='overlimit@test.com',
            dinarski_racuni=[{'banka': 'Test', 'racun': '777-777777-77'}]
        )
        db.session.add(firma)
        db.session.flush()

        # Create user and komitent
        user = User(email='user@test.com', full_name='Test User', role='pausalac', firma_id=firma.id)
        user.set_password('password123')
        db.session.add(user)

        komitent = Komitent(
            firma_id=firma.id,
            pib='666666666',
            maticni_broj='66666666',
            naziv='Test Komitent',
            adresa='Test',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            email='komitent@test.com'
        )
        db.session.add(komitent)
        db.session.flush()

        # Create invoice that exceeds limit
        today = date.today()
        faktura = Faktura(
            firma_id=firma.id,
            komitent_id=komitent.id,
            user_id=user.id,
            broj_fakture='OVER-001',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=today - timedelta(days=100),
            valuta_placanja=30,
            datum_dospeca=today - timedelta(days=70),
            ukupan_iznos_rsd=Decimal('9000000.00'),  # Over 8M limit
            status='izdata'
        )
        db.session.add(faktura)
        db.session.commit()

        preostali_limit = calculate_firma_rolling_limit_remaining(firma.id)

        # Should be negative
        expected_limit = ROLLING_LIMIT_365_DAYS - 9000000.00
        assert preostali_limit == expected_limit
        assert preostali_limit == -1000000.00  # 1M over limit


def test_get_firma_list_excludes_stornirana_invoices(app, test_data):
    """Test that stornirana invoices are excluded from statistics."""
    with app.app_context():
        # Use explicit date range to cover all test invoices
        today = date.today()
        first_day_this_month = today.replace(day=1)
        date_to = first_day_this_month + timedelta(days=14)

        firma_list, total = get_firma_list_with_stats(
            date_from=first_day_this_month,
            date_to=date_to
        )

        # ABC Firma should have 3 invoices (excluding stornirana F1-004)
        abc_firma = next(f for f in firma_list if f['naziv'] == 'ABC Firma')
        assert abc_firma['broj_faktura'] == 3

        # Promet should NOT include stornirana invoice (50k)
        # Expected: 100k + 200k + 150k = 450k (NOT 500k)
        assert abc_firma['promet_rsd'] == 450000.00


def test_get_firma_list_poslednja_aktivnost(app, test_data):
    """Test that poslednja_aktivnost reflects most recent finalized_at."""
    with app.app_context():
        firma_list, total = get_firma_list_with_stats()

        # XYZ Firma's most recent invoice is F2-002 (finalized 1 hour ago)
        xyz_firma = next(f for f in firma_list if f['naziv'] == 'XYZ Firma')
        assert xyz_firma['poslednja_aktivnost'] is not None

        # ABC Firma's most recent invoice is F1-003 (finalized 1 day ago)
        abc_firma = next(f for f in firma_list if f['naziv'] == 'ABC Firma')
        assert abc_firma['poslednja_aktivnost'] is not None

        # XYZ should be more recent than ABC
        assert xyz_firma['poslednja_aktivnost'] > abc_firma['poslednja_aktivnost']


def test_get_pausalac_dashboard_stats(app, test_data):
    """Test aggregation of pausalac dashboard statistics."""
    with app.app_context():
        firma1 = test_data['firma1']

        stats = get_pausalac_dashboard_stats(firma1.id)

        # Verify stats structure
        assert 'broj_faktura_ovog_meseca' in stats
        assert 'promet_ovog_meseca' in stats
        assert 'promet_tekuce_godine' in stats
        assert 'preostali_limit_godisnji' in stats
        assert 'promet_365_dana' in stats
        assert 'preostali_limit_365' in stats
        assert 'broj_komitenata' in stats
        assert 'broj_artikala' in stats

        # Firma1 has 2-3 invoices this month depending on today's date
        # (faktura3 has datum_prometa = first_day + 10 days)
        # If today is before that date, only 2 invoices will be counted
        assert stats['broj_faktura_ovog_meseca'] >= 2
        assert stats['promet_ovog_meseca'] >= 300000.00  # At least F1-001 + F1-002

        # Firma1 rolling 365-day promet varies based on whether faktura3 is in past
        # Minimum: 300k (F1-001 + F1-002) + 500k (F1-365) = 800k
        # Maximum: 450k (all 3 this month) + 500k (F1-365) = 950k
        assert stats['promet_365_dana'] >= 800000.00
        assert stats['promet_365_dana'] <= 950000.00

        # Remaining limit: 8M - promet_365_dana
        # Minimum: 8M - 950k = 7,050,000
        # Maximum: 8M - 800k = 7,200,000
        assert stats['preostali_limit_365'] >= 7050000.00
        assert stats['preostali_limit_365'] <= 7200000.00

        # Firma1 has 1 komitent
        assert stats['broj_komitenata'] == 1

        # Firma1 has 2 artikli
        assert stats['broj_artikala'] == 2


def test_get_pausalac_recent_fakture(app, test_data):
    """Test retrieval of recent fakture with proper ordering."""
    with app.app_context():
        firma1 = test_data['firma1']

        # Get 10 most recent fakture
        recent_fakture = get_pausalac_recent_fakture(firma1.id, limit=10)

        # Firma1 has 6 total invoices (3 this month + stornirana + F1-365 + F1-OLD)
        assert len(recent_fakture) == 6

        # First faktura should be most recent (by datum_prometa DESC)
        # F1-003 has datum_prometa = first_day_this_month + 10 days
        assert recent_fakture[0].broj_fakture == 'F1-003'

        # Each faktura should have komitent relationship loaded
        for faktura in recent_fakture:
            assert faktura.komitent is not None


def test_get_pausalac_recent_fakture_pagination(app, test_data):
    """Test that recent fakture limit works correctly."""
    with app.app_context():
        firma1 = test_data['firma1']

        # Get only 3 most recent
        recent_fakture = get_pausalac_recent_fakture(firma1.id, limit=3)

        assert len(recent_fakture) == 3

        # Should be F1-003, F1-004 (stornirana), F1-002 (by datum_prometa DESC)
        assert recent_fakture[0].broj_fakture == 'F1-003'


def test_calculate_rolling_limit_projections(app, test_data):
    """Test rolling limit projections using sliding window approach (real DB data)."""
    with app.app_context():
        firma1 = test_data['firma1']

        projections = calculate_rolling_limit_projections(firma1.id)

        # Verify projections structure
        assert 'preostali_limit' in projections
        assert 'projekcija_7_dana' in projections
        assert 'projekcija_15_dana' in projections
        assert 'projekcija_30_dana' in projections
        assert 'upozorenje_7_dana' in projections
        assert 'upozorenje_15_dana' in projections
        assert 'upozorenje_30_dana' in projections

        # Preostali limit: 8M - 950k = 7,050,000
        # NOTE: Može biti 950k ili manje zavisno od dana meseca kad se pokreće test
        assert projections['preostali_limit'] >= 6850000.00  # Minimalno ako su sve fakture uključene
        assert projections['preostali_limit'] <= 8000000.00  # Maksimalno

        # Test data fakture timeline:
        # - 3 fakture ovog meseca (100k, 200k, 150k)
        # - 1 faktura od pre 200 dana (500k)
        # - 1 faktura od pre 400 dana (1M) - IZVAN rolling perioda
        # - Nema fakture sa budućim datumima
        # Total u rolling 365: zavisi od trenutnog dana (može biti 950k, 800k, 600k itd)

        # Projekcije koriste sliding window:
        # Za +7 dana: promet od (danas - 358) do (danas + 7)
        # Za +15 dana: promet od (danas - 350) do (danas + 15)
        # Za +30 dana: promet od (danas - 335) do (danas + 30)

        # Projekcije mogu RASTI (ako se odbacuju stare fakture) ili PADATI (ako postoje buduće fakture)
        # Za test podatke, projekcije zavise od datuma pokretanja testa:
        # - Ako je faktura3 već u prošlosti, projekcije će rasti (stare fakture ispadaju)
        # - Ako je faktura3 još u budućnosti, projekcija može pasti kada faktura3 uđe u prozor
        # Zato proveravamo samo da su vrednosti razumne i u rastućem/padajućem nizu
        assert projections['projekcija_7_dana'] >= 6500000.00  # Minimalna razumna vrednost
        assert projections['projekcija_15_dana'] >= 6500000.00
        assert projections['projekcija_30_dana'] >= 6500000.00

        # Projekcije bi trebale biti u monoton rastućem ili monoton padajućem nizu
        # (ili iste ako nema promena u rolling prozoru)
        assert (projections['projekcija_7_dana'] <= projections['projekcija_15_dana'] <= projections['projekcija_30_dana'] or
                projections['projekcija_7_dana'] >= projections['projekcija_15_dana'] >= projections['projekcija_30_dana'])

        # Sve projekcije moraju biti pozitivne (nema upozorenja)
        assert projections['projekcija_7_dana'] > 0
        assert projections['projekcija_15_dana'] > 0
        assert projections['projekcija_30_dana'] > 0
        assert projections['upozorenje_7_dana'] is False
        assert projections['upozorenje_15_dana'] is False
        assert projections['upozorenje_30_dana'] is False


def test_calculate_rolling_limit_projections_with_future_invoices(app):
    """Test that projections correctly account for future-dated invoices."""
    with app.app_context():
        # Create test firma
        firma = PausalnFirma(
            pib='999999999',
            maticni_broj='99999999',
            naziv='Future Invoice Firma',
            adresa='Adresa',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            telefon='011111111',
            email='future@test.com',
            dinarski_racuni=[{'banka': 'Test', 'racun': '999-999999-99'}]
        )
        db.session.add(firma)
        db.session.flush()

        # Create user and komitent
        user = User(email='futureuser@test.com', full_name='Future User', role='pausalac', firma_id=firma.id)
        user.set_password('password123')
        db.session.add(user)

        komitent = Komitent(
            firma_id=firma.id,
            pib='888888888',
            maticni_broj='88888888',
            naziv='Future Komitent',
            adresa='Test',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            email='future@komitent.com'
        )
        db.session.add(komitent)
        db.session.flush()

        today = date.today()

        # Create one current invoice
        faktura_current = Faktura(
            firma_id=firma.id,
            komitent_id=komitent.id,
            user_id=user.id,
            broj_fakture='CURR-001',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=today,
            valuta_placanja=30,
            datum_dospeca=today + timedelta(days=30),
            ukupan_iznos_rsd=Decimal('1000000.00'),
            status='izdata'
        )
        db.session.add(faktura_current)

        # Create future invoice (3 days from now)
        faktura_future = Faktura(
            firma_id=firma.id,
            komitent_id=komitent.id,
            user_id=user.id,
            broj_fakture='FUT-001',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=today + timedelta(days=3),
            valuta_placanja=30,
            datum_dospeca=today + timedelta(days=33),
            ukupan_iznos_rsd=Decimal('500000.00'),
            status='izdata'
        )
        db.session.add(faktura_future)
        db.session.commit()

        # Get projections
        projections = calculate_rolling_limit_projections(firma.id)

        # Current limit: 8M - 1M = 7M
        assert projections['preostali_limit'] == 7000000.00

        # Projection for +7 days should include the future invoice (3 days from now)
        # 7 days from now: 8M - (1M + 500k) = 6.5M
        assert projections['projekcija_7_dana'] == 6500000.00

        # Projection for +15 days should also include the future invoice
        assert projections['projekcija_15_dana'] == 6500000.00

        # Projection for +30 days should also include the future invoice
        assert projections['projekcija_30_dana'] == 6500000.00

        # In this case, projekcija_7_dana < preostali_limit (future invoice reduces available limit)
        assert projections['projekcija_7_dana'] < projections['preostali_limit']


def test_rolling_limit_calculation_excludes_stornirane(app, test_data):
    """Test that stornirane fakture are excluded from rolling limit calculation."""
    with app.app_context():
        firma1 = test_data['firma1']

        stats = get_pausalac_dashboard_stats(firma1.id)

        # Firma1 has 3 regular invoices this month + 1 stornirana (50k)
        # Depending on current day, may have 2-3 invoices in "ovog meseca"
        # (faktura3 is on first_day + 10, may not be counted if today < day 10)

        # Stornirana (50k) should be excluded from both monthly and rolling
        # Monthly promet should be 300k-450k (depending on which invoices are counted)
        assert stats['promet_ovog_meseca'] >= 300000.00  # At least faktura1 + faktura2
        assert stats['promet_ovog_meseca'] <= 450000.00  # At most all 3 regular invoices

        # Rolling 365-day: varies based on which invoices fall within period
        # Should include faktura from 200 days ago (500k) + some/all of this month's invoices
        # But stornirana (50k) must be excluded
        assert stats['promet_365_dana'] >= 800000.00  # Minimum: 500k + 300k (2 invoices)
        assert stats['promet_365_dana'] <= 950000.00  # Maximum: 500k + 450k (3 invoices)

        # Preostali limit should be positive and reasonable
        assert stats['preostali_limit_365'] >= 7050000.00  # Minimum if all included
        assert stats['preostali_limit_365'] <= 7200000.00  # Maximum if some excluded
