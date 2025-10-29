"""Unit tests for Faktura Service."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.komitent import Komitent
from app.models.faktura import Faktura
from app.services.faktura_service import create_faktura


@pytest.fixture
def pausalac_with_firma(app):
    """Create a test pausalac user with firma."""
    with app.app_context():
        firma = PausalnFirma(
            pib='123456789',
            maticni_broj='12345678',
            naziv='Test Firma',
            adresa='Test Adresa',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            telefon='011111111',
            email='firma@test.com',
            dinarski_racuni=[{'banka': 'Test Banka', 'racun': '123-456789-00'}],
            prefiks_fakture='TF-',
            sufiks_fakture='/2025',
            brojac_fakture=1
        )
        db.session.add(firma)
        db.session.commit()

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


def create_foreign_komitent(firma_id):
    """Helper function to create a foreign komitent with devizni računi."""
    komitent = Komitent(
        firma_id=firma_id,
        pib='98765432',
        maticni_broj='87654321',
        naziv='Foreign Client Ltd.',
        adresa='Main Street',
        broj='100',
        postanski_broj='10000',
        mesto='Berlin',
        drzava='Germany',
        email='contact@foreignclient.com',
        devizni_racuni=[{
            'banka': 'Test Bank',
            'iban': 'DE89370400440532013000',
            'swift': 'COBADEFFXXX',
            'valuta': 'EUR'
        }]
    )
    db.session.add(komitent)
    db.session.commit()
    return komitent


class TestCreateDeviznaFaktura:
    """Tests for creating foreign currency invoices."""

    @patch('app.services.faktura_service.get_kurs')
    def test_create_devizna_faktura_with_nbs_kurs(self, mock_get_kurs, app, pausalac_with_firma):
        """Test creating foreign currency invoice with NBS exchange rate."""
        with app.app_context():
            user, firma = pausalac_with_firma
            komitent = create_foreign_komitent(firma.id)
            mock_get_kurs.return_value = Decimal('117.5432')

            data = {
                'tip_fakture': 'devizna',
                'valuta_fakture': 'EUR',
                'komitent_id': komitent.id,
                'datum_prometa': date.today(),
                'valuta_placanja': 7,
                'stavke': [
                    {
                        'naziv': 'Consulting Services',
                        'kolicina': Decimal('10.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('100.00')
                    }
                ]
            }

            faktura = create_faktura(data, user)

            assert faktura.id is not None
            assert faktura.tip_fakture == 'devizna'
            assert faktura.valuta_fakture == 'EUR'
            assert faktura.srednji_kurs == Decimal('117.5432')
            assert faktura.ukupan_iznos_originalna_valuta == Decimal('1000.00')  # 10 * 100
            assert faktura.ukupan_iznos_rsd == Decimal('117543.20')  # 1000 * 117.5432
            assert faktura.jezik == 'en'  # Foreign currency invoices are in English
            assert faktura.status == 'draft'

            # Verify get_kurs was called
            mock_get_kurs.assert_called_once_with('EUR', date.today())

    @patch('app.services.faktura_service.get_kurs')
    def test_create_devizna_faktura_with_manual_override_kurs(self, mock_get_kurs, app, pausalac_with_firma):
        """Test creating foreign currency invoice with manual override kurs."""
        with app.app_context():
            user, firma = pausalac_with_firma
            komitent = create_foreign_komitent(firma.id)

            data = {
                'tip_fakture': 'devizna',
                'valuta_fakture': 'EUR',
                'srednji_kurs': Decimal('120.0000'),  # Manual override
                'komitent_id': komitent.id,
                'datum_prometa': date.today(),
                'valuta_placanja': 7,
                'stavke': [
                    {
                        'naziv': 'Consulting Services',
                        'kolicina': Decimal('10.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('100.00')
                    }
                ]
            }

            faktura = create_faktura(data, user)

            assert faktura.srednji_kurs == Decimal('120.0000')
            assert faktura.ukupan_iznos_rsd == Decimal('120000.00')  # 1000 * 120

            # Verify get_kurs was NOT called (manual override)
            mock_get_kurs.assert_not_called()

    def test_create_devizna_faktura_calculates_rsd_correctly(self, app, pausalac_with_firma):
        """Test that RSD amount is calculated correctly for foreign currency invoice."""
        with app.app_context():
            user, firma = pausalac_with_firma
            komitent = create_foreign_komitent(firma.id)

            data = {
                'tip_fakture': 'devizna',
                'valuta_fakture': 'USD',
                'srednji_kurs': Decimal('105.2500'),
                'komitent_id': komitent.id,
                'datum_prometa': date.today(),
                'valuta_placanja': 7,
                'stavke': [
                    {
                        'naziv': 'Software Development',
                        'kolicina': Decimal('20.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('50.00')
                    }
                ]
            }

            faktura = create_faktura(data, user)

            # 20 * 50 = 1000 USD
            # 1000 * 105.25 = 105250 RSD
            assert faktura.ukupan_iznos_originalna_valuta == Decimal('1000.00')
            assert faktura.ukupan_iznos_rsd == Decimal('105250.00')

    @patch('app.services.faktura_service.get_kurs')
    def test_create_devizna_faktura_raises_error_if_nbs_unavailable(self, mock_get_kurs, app, pausalac_with_firma):
        """Test that error is raised if NBS kurs is unavailable and no manual override."""
        with app.app_context():
            user, firma = pausalac_with_firma
            komitent = create_foreign_komitent(firma.id)
            mock_get_kurs.return_value = None  # NBS unavailable

            data = {
                'tip_fakture': 'devizna',
                'valuta_fakture': 'EUR',
                # No srednji_kurs provided
                'komitent_id': komitent.id,
                'datum_prometa': date.today(),
                'valuta_placanja': 7,
                'stavke': [
                    {
                        'naziv': 'Consulting',
                        'kolicina': Decimal('10.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('100.00')
                    }
                ]
            }

            with pytest.raises(ValueError) as exc_info:
                create_faktura(data, user)

            assert 'NBS kurs nije dostupan' in str(exc_info.value)

    def test_create_devizna_faktura_sets_jezik_en(self, app, pausalac_with_firma):
        """Test that foreign currency invoices have jezik='en'."""
        with app.app_context():
            user, firma = pausalac_with_firma
            komitent = create_foreign_komitent(firma.id)

            data = {
                'tip_fakture': 'devizna',
                'valuta_fakture': 'GBP',
                'srednji_kurs': Decimal('145.7800'),
                'komitent_id': komitent.id,
                'datum_prometa': date.today(),
                'valuta_placanja': 7,
                'stavke': [
                    {
                        'naziv': 'Design Services',
                        'kolicina': Decimal('5.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('80.00')
                    }
                ]
            }

            faktura = create_faktura(data, user)

            assert faktura.jezik == 'en'

    def test_create_standardna_faktura_only_rsd(self, app, pausalac_with_firma):
        """Test that standardna faktura has only RSD amount, no foreign currency."""
        with app.app_context():
            user, firma = pausalac_with_firma

            # Create domestic komitent
            komitent = Komitent(
                firma_id=firma.id,
                pib='11111111',
                maticni_broj='11111111',
                naziv='Domestic Client d.o.o.',
                adresa='Knez Mihailova',
                broj='15',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='contact@domestic.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            data = {
                'tip_fakture': 'standardna',
                'komitent_id': komitent.id,
                'datum_prometa': date.today(),
                'valuta_placanja': 7,
                'stavke': [
                    {
                        'naziv': 'Usluge konsaltinga',
                        'kolicina': Decimal('10.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('5000.00')
                    }
                ]
            }

            faktura = create_faktura(data, user)

            assert faktura.valuta_fakture == 'RSD'
            assert faktura.ukupan_iznos_rsd == Decimal('50000.00')
            assert faktura.ukupan_iznos_originalna_valuta is None
            assert faktura.srednji_kurs is None
            assert faktura.jezik == 'sr'  # Serbian for domestic invoices
