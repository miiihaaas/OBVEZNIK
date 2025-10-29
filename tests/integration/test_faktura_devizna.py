"""Integration tests for foreign currency (devizna) invoices with NBS exchange rates."""
import pytest
from unittest.mock import patch
from decimal import Decimal
from datetime import date
from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.komitent import Komitent
from app.services.faktura_service import create_faktura


@pytest.fixture
def pausalac_user(app):
    """Create a pausalac user with firma for testing."""
    firma = PausalnFirma(
        pib='123456789',
        maticni_broj='12345678',
        naziv='Test Firma',
        adresa='Test Address',
        broj='1',
        mesto='Belgrade',
        postanski_broj='11000',
        email='test@firma.com',
        telefon='+381111111111',
        dinarski_racuni=['111-111111-11'],
        prefiks_fakture='TF-',
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
    return user


@pytest.fixture
def komitent(app, pausalac_user):
    """Create a komitent with devizni računi for foreign currency invoices."""
    komitent = Komitent(
        firma_id=pausalac_user.firma_id,
        pib='987654321',
        maticni_broj='87654321',
        naziv='Test Komitent',
        adresa='Komitent Address',
        broj='10',
        mesto='Belgrade',
        postanski_broj='11000',
        drzava='Srbija',
        email='test@komitent.com',
        devizni_racuni=[{
            'banka': 'Test Banka',
            'iban': 'RS35260005601001611379',
            'swift': 'BEOBBGRXXX',
            'valuta': 'EUR'
        }]
    )
    db.session.add(komitent)
    db.session.commit()
    return komitent


@pytest.fixture
def komitent_bez_deviznih_racuna(app, pausalac_user):
    """Create a komitent without devizni računi for testing validation."""
    komitent = Komitent(
        firma_id=pausalac_user.firma_id,
        pib='111222333',
        maticni_broj='11122233',
        naziv='Test Komitent Bez Deviznih Računa',
        adresa='Test Address',
        broj='5',
        mesto='Belgrade',
        postanski_broj='11000',
        drzava='Srbija',
        email='test2@komitent.com'
    )
    db.session.add(komitent)
    db.session.commit()
    return komitent


class TestDeviznaFaktura:
    """Integration tests for foreign currency invoices."""

    @patch('app.services.faktura_service.get_kurs')
    def test_create_devizna_faktura_with_nbs_kurs(self, mock_get_kurs, app, pausalac_user, komitent):
        """Test creating foreign currency invoice with NBS exchange rate."""
        with app.app_context():
            # Mock NBS exchange rate (EUR to RSD)
            mock_get_kurs.return_value = Decimal('117.5432')

            # Invoice data
            data = {
                'komitent_id': komitent.id,
                'tip_fakture': 'devizna',  # Must be 'devizna' for foreign currency
                'valuta_fakture': 'EUR',  # Foreign currency
                'datum_prometa': date.today(),
                'valuta_placanja': 30,
                'stavke': [
                    {
                        'naziv': 'Test Product',
                        'kolicina': 10,
                        'jedinica_mere': 'kom',
                        'cena': 100.00  # 100 EUR
                    }
                ]
            }

            # Create invoice
            faktura = create_faktura(data, pausalac_user)

            # Assertions
            assert faktura is not None
            assert faktura.valuta_fakture == 'EUR'
            assert faktura.srednji_kurs == Decimal('117.5432')
            assert faktura.ukupan_iznos_originalna_valuta == Decimal('1000.00')  # 10 * 100 EUR
            assert faktura.ukupan_iznos_rsd == Decimal('1000.00') * Decimal('117.5432')  # EUR * kurs

            # Verify get_kurs was called
            mock_get_kurs.assert_called_once_with('EUR', date.today())

    @patch('app.services.faktura_service.get_kurs')
    def test_create_devizna_faktura_nbs_unavailable_manual_override(self, mock_get_kurs, app, pausalac_user, komitent):
        """Test creating foreign currency invoice with manual kurs override when NBS is unavailable."""
        with app.app_context():
            # Mock NBS returning None (not available)
            mock_get_kurs.return_value = None

            # Invoice data with manual kurs override
            data = {
                'komitent_id': komitent.id,
                'tip_fakture': 'devizna',  # Must be 'devizna' for foreign currency
                'valuta_fakture': 'EUR',
                'datum_prometa': date.today(),
                'valuta_placanja': 30,
                'srednji_kurs': '118.0000',  # Manual override (not srednji_kurs_override)
                'stavke': [
                    {
                        'naziv': 'Test Product',
                        'kolicina': 5,
                        'jedinica_mere': 'kom',
                        'cena': 200.00  # 200 EUR
                    }
                ]
            }

            # Create invoice
            faktura = create_faktura(data, pausalac_user)

            # Assertions
            assert faktura is not None
            assert faktura.valuta_fakture == 'EUR'
            assert faktura.srednji_kurs == Decimal('118.0000')  # Manual override used
            assert faktura.ukupan_iznos_originalna_valuta == Decimal('1000.00')  # 5 * 200 EUR
            assert faktura.ukupan_iznos_rsd == Decimal('1000.00') * Decimal('118.0000')

    @patch('app.services.faktura_service.get_kurs')
    def test_create_devizna_faktura_nbs_unavailable_no_override_fails(self, mock_get_kurs, app, pausalac_user, komitent):
        """Test creating foreign currency invoice fails when NBS is unavailable and no manual override."""
        with app.app_context():
            # Mock NBS returning None (not available)
            mock_get_kurs.return_value = None

            # Invoice data WITHOUT manual kurs override
            data = {
                'komitent_id': komitent.id,
                'tip_fakture': 'devizna',  # Must be 'devizna' for foreign currency
                'valuta_fakture': 'USD',
                'datum_prometa': date.today(),
                'valuta_placanja': 30,
                'stavke': [
                    {
                        'naziv': 'Test Product',
                        'kolicina': 1,
                        'jedinica_mere': 'kom',
                        'cena': 500.00
                    }
                ]
            }

            # Attempt to create invoice - should raise ValueError
            with pytest.raises(ValueError) as exc_info:
                create_faktura(data, pausalac_user)

            # Assertions
            assert 'NBS kurs nije dostupan' in str(exc_info.value)
            assert 'USD' in str(exc_info.value)

    def test_create_domestic_faktura_no_nbs_call(self, app, pausalac_user, komitent):
        """Test creating domestic (RSD) invoice does not call NBS service."""
        with app.app_context():
            # Invoice data in RSD (no NBS call needed)
            data = {
                'komitent_id': komitent.id,
                'tip_fakture': 'standardna',
                'valuta_fakture': 'RSD',  # Domestic currency
                'datum_prometa': date.today(),
                'valuta_placanja': 30,
                'stavke': [
                    {
                        'naziv': 'Test Product',
                        'kolicina': 10,
                        'jedinica_mere': 'kom',
                        'cena': 1000.00  # 1000 RSD
                    }
                ]
            }

            # Create invoice
            with patch('app.services.faktura_service.get_kurs') as mock_get_kurs:
                faktura = create_faktura(data, pausalac_user)

                # Assertions
                assert faktura is not None
                assert faktura.valuta_fakture == 'RSD'
                assert faktura.srednji_kurs is None
                assert faktura.ukupan_iznos_rsd == Decimal('10000.00')  # 10 * 1000 RSD
                assert faktura.ukupan_iznos_originalna_valuta is None

                # Verify get_kurs was NOT called
                mock_get_kurs.assert_not_called()

    @patch('app.services.faktura_service.get_kurs')
    def test_create_devizna_faktura_multiple_stavke(self, mock_get_kurs, app, pausalac_user, komitent):
        """Test creating foreign currency invoice with multiple line items."""
        with app.app_context():
            # Mock NBS exchange rate
            mock_get_kurs.return_value = Decimal('135.6789')  # GBP to RSD

            # Invoice data with multiple stavke
            data = {
                'komitent_id': komitent.id,
                'tip_fakture': 'devizna',  # Must be 'devizna' for foreign currency
                'valuta_fakture': 'GBP',
                'datum_prometa': date.today(),
                'valuta_placanja': 30,
                'stavke': [
                    {
                        'naziv': 'Product A',
                        'kolicina': 5,
                        'jedinica_mere': 'kom',
                        'cena': 50.00  # 50 GBP
                    },
                    {
                        'naziv': 'Product B',
                        'kolicina': 3,
                        'jedinica_mere': 'kom',
                        'cena': 100.00  # 100 GBP
                    }
                ]
            }

            # Create invoice
            faktura = create_faktura(data, pausalac_user)

            # Assertions
            assert faktura is not None
            assert faktura.valuta_fakture == 'GBP'
            assert faktura.srednji_kurs == Decimal('135.6789')
            # Total: (5 * 50) + (3 * 100) = 250 + 300 = 550 GBP
            assert faktura.ukupan_iznos_originalna_valuta == Decimal('550.00')
            # RSD amount is rounded to 2 decimal places (DECIMAL(12,2) in DB)
            expected_rsd = (Decimal('550.00') * Decimal('135.6789')).quantize(Decimal('0.01'))
            assert faktura.ukupan_iznos_rsd == expected_rsd
            assert len(faktura.stavke) == 2

    @patch('app.services.faktura_service.get_kurs')
    def test_manual_override_takes_precedence_over_nbs(self, mock_get_kurs, app, pausalac_user, komitent):
        """Test manual kurs override takes precedence over NBS rate."""
        with app.app_context():
            # Mock NBS returning a rate
            mock_get_kurs.return_value = Decimal('117.5432')

            # Invoice data with manual override (should use this instead of NBS)
            data = {
                'komitent_id': komitent.id,
                'tip_fakture': 'devizna',  # Must be 'devizna' for foreign currency
                'valuta_fakture': 'EUR',
                'datum_prometa': date.today(),
                'valuta_placanja': 30,
                'srednji_kurs': '120.0000',  # Manual override (not srednji_kurs_override)
                'stavke': [
                    {
                        'naziv': 'Test Product',
                        'kolicina': 10,
                        'jedinica_mere': 'kom',
                        'cena': 100.00
                    }
                ]
            }

            # Create invoice
            faktura = create_faktura(data, pausalac_user)

            # Assertions - should use manual override, not NBS rate
            assert faktura.srednji_kurs == Decimal('120.0000')  # Not 117.5432
            assert faktura.ukupan_iznos_rsd == Decimal('1000.00') * Decimal('120.0000')

    @patch('app.services.faktura_service.get_kurs')
    def test_devizna_faktura_requires_komitent_with_devizni_racun(self, mock_get_kurs, app, pausalac_user, komitent_bez_deviznih_racuna):
        """Test that creating devizna faktura fails if komitent doesn't have devizni račun."""
        with app.app_context():
            # Mock NBS exchange rate
            mock_get_kurs.return_value = Decimal('117.5432')

            # Invoice data with komitent that lacks devizni računi
            data = {
                'komitent_id': komitent_bez_deviznih_racuna.id,
                'tip_fakture': 'devizna',
                'valuta_fakture': 'EUR',
                'datum_prometa': date.today(),
                'valuta_placanja': 30,
                'stavke': [
                    {
                        'naziv': 'Test Product',
                        'kolicina': 1,
                        'jedinica_mere': 'kom',
                        'cena': 100.00
                    }
                ]
            }

            # Attempt to create invoice - should raise ValueError
            with pytest.raises(ValueError) as exc_info:
                create_faktura(data, pausalac_user)

            # Assertions
            assert 'devizni račun' in str(exc_info.value).lower()

    @patch('app.services.faktura_service.get_kurs')
    def test_devizna_faktura_displays_dual_currency_in_detail_view(self, mock_get_kurs, app, pausalac_user, komitent):
        """Test that devizna faktura has dual currency data for display."""
        with app.app_context():
            # Mock NBS exchange rate
            mock_get_kurs.return_value = Decimal('117.5432')

            # Invoice data
            data = {
                'komitent_id': komitent.id,
                'tip_fakture': 'devizna',
                'valuta_fakture': 'EUR',
                'datum_prometa': date.today(),
                'valuta_placanja': 30,
                'stavke': [
                    {
                        'naziv': 'Test Product',
                        'kolicina': 10,
                        'jedinica_mere': 'kom',
                        'cena': 100.00  # 100 EUR
                    }
                ]
            }

            # Create invoice
            faktura = create_faktura(data, pausalac_user)
            db.session.commit()

            # Assertions - verify dual currency data is stored
            assert faktura.valuta_fakture == 'EUR'
            assert faktura.srednji_kurs == Decimal('117.5432')
            assert faktura.ukupan_iznos_originalna_valuta == Decimal('1000.00')
            # RSD equivalent: 1000 * 117.5432 = 117543.20
            expected_rsd = (Decimal('1000.00') * Decimal('117.5432')).quantize(Decimal('0.01'))
            assert faktura.ukupan_iznos_rsd == expected_rsd
            assert faktura.jezik == 'en'  # Should be English for foreign currency

    @patch('app.services.faktura_service.get_kurs')
    def test_dual_currency_display_in_ukupan_iznos(self, mock_get_kurs, app, pausalac_user, komitent):
        """Test that ukupan iznos shows both currencies correctly."""
        with app.app_context():
            # Mock NBS exchange rate for USD
            mock_get_kurs.return_value = Decimal('108.2345')

            # Invoice data
            data = {
                'komitent_id': komitent.id,
                'tip_fakture': 'devizna',
                'valuta_fakture': 'USD',
                'datum_prometa': date.today(),
                'valuta_placanja': 30,
                'stavke': [
                    {
                        'naziv': 'Consulting Services',
                        'kolicina': 20,
                        'jedinica_mere': 'h',
                        'cena': 50.00  # 50 USD per hour
                    }
                ]
            }

            # Create invoice
            faktura = create_faktura(data, pausalac_user)

            # Assertions
            assert faktura.valuta_fakture == 'USD'
            assert faktura.ukupan_iznos_originalna_valuta == Decimal('1000.00')  # 20 * 50 USD
            # RSD calculation: 1000 * 108.2345 = 108234.50
            expected_rsd = (Decimal('1000.00') * Decimal('108.2345')).quantize(Decimal('0.01'))
            assert faktura.ukupan_iznos_rsd == expected_rsd
            assert faktura.srednji_kurs == Decimal('108.2345')

            # Verify both amounts are stored correctly
            assert faktura.ukupan_iznos_originalna_valuta is not None
            assert faktura.ukupan_iznos_rsd is not None
            assert faktura.ukupan_iznos_rsd > faktura.ukupan_iznos_originalna_valuta  # RSD should be larger
