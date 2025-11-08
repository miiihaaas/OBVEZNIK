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
from app.services.faktura_service import create_faktura, update_faktura, generate_broj_fakture, finalize_faktura


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


@pytest.fixture
def komitent(pausalac_with_firma):
    """Create a test komitent for the pausalac's firma."""
    user, firma = pausalac_with_firma
    komitent = Komitent(
        firma_id=firma.id,
        pib='87654321',
        maticni_broj='12345678',
        naziv='Test Komitent',
        adresa='Komitent Adresa',
        broj='2',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        email='komitent@test.rs'
    )
    db.session.add(komitent)
    db.session.commit()
    return komitent


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

    def test_create_devizna_faktura_without_valuta_raises_error(self, app, pausalac_with_firma):
        """Test that devizna faktura without valuta raises ValidationError."""
        with app.app_context():
            user, firma = pausalac_with_firma
            komitent = create_foreign_komitent(firma.id)

            data = {
                'tip_fakture': 'devizna',
                # No valuta_fakture provided
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

            assert 'Devizna faktura mora imati valutu' in str(exc_info.value)

    def test_create_devizna_faktura_with_rsd_raises_error(self, app, pausalac_with_firma):
        """Test that devizna faktura with RSD valuta raises ValidationError."""
        with app.app_context():
            user, firma = pausalac_with_firma
            komitent = create_foreign_komitent(firma.id)

            data = {
                'tip_fakture': 'devizna',
                'valuta_fakture': 'RSD',  # Invalid for devizna
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

            assert 'Devizna faktura mora imati valutu' in str(exc_info.value)


class TestUpdateFaktura:
    """Tests for updating draft invoices."""

    def test_update_faktura_successfully_updates_draft(self, app, pausalac_with_firma):
        """Test that update_faktura successfully updates a draft invoice."""
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

            # Create draft faktura
            data = {
                'tip_fakture': 'standardna',
                'komitent_id': komitent.id,
                'datum_prometa': date.today(),
                'valuta_placanja': 7,
                'stavke': [
                    {
                        'naziv': 'Usluga 1',
                        'kolicina': Decimal('1.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('100.00')
                    }
                ]
            }
            faktura = create_faktura(data, user)
            assert faktura.ukupan_iznos_rsd == Decimal('100.00')
            assert faktura.valuta_placanja == 7

            # Update faktura
            updated_data = {
                'tip_fakture': 'standardna',
                'komitent_id': komitent.id,
                'datum_prometa': date.today(),
                'valuta_placanja': 14,  # Changed
                'stavke': [
                    {
                        'naziv': 'Usluga 2',
                        'kolicina': Decimal('2.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('200.00')
                    }
                ]
            }
            updated_faktura = update_faktura(faktura.id, updated_data, user)

            assert updated_faktura.valuta_placanja == 14
            assert updated_faktura.ukupan_iznos_rsd == Decimal('400.00')
            assert len(updated_faktura.stavke) == 1
            assert updated_faktura.stavke[0].naziv == 'Usluga 2'
            assert updated_faktura.status == 'draft'  # Status unchanged

    def test_update_faktura_raises_error_for_izdata_invoice(self, app, pausalac_with_firma):
        """Test that update_faktura raises ValueError for issued invoices."""
        with app.app_context():
            user, firma = pausalac_with_firma

            # Create domestic komitent
            komitent = Komitent(
                firma_id=firma.id,
                pib='22222222',
                maticni_broj='22222222',
                naziv='Client 2',
                adresa='Adresa 2',
                broj='2',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='client2@test.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            # Create faktura
            data = {
                'tip_fakture': 'standardna',
                'komitent_id': komitent.id,
                'datum_prometa': date.today(),
                'valuta_placanja': 7,
                'stavke': [
                    {
                        'naziv': 'Usluga',
                        'kolicina': Decimal('1.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('100.00')
                    }
                ]
            }
            faktura = create_faktura(data, user)

            # Change status to 'izdata' manually (simulating finalization)
            faktura.status = 'izdata'
            db.session.commit()

            # Try to update
            updated_data = {
                'tip_fakture': 'standardna',
                'komitent_id': komitent.id,
                'datum_prometa': date.today(),
                'valuta_placanja': 14,
                'stavke': [
                    {
                        'naziv': 'New Usluga',
                        'kolicina': Decimal('1.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('200.00')
                    }
                ]
            }

            with pytest.raises(ValueError) as exc_info:
                update_faktura(faktura.id, updated_data, user)

            assert "Cannot update faktura with status 'izdata'" in str(exc_info.value)
            assert "Only draft invoices can be edited" in str(exc_info.value)

    def test_update_faktura_raises_error_for_stornirana_invoice(self, app, pausalac_with_firma):
        """Test that update_faktura raises ValueError for stornirane invoices."""
        with app.app_context():
            user, firma = pausalac_with_firma

            # Create domestic komitent
            komitent = Komitent(
                firma_id=firma.id,
                pib='33333333',
                maticni_broj='33333333',
                naziv='Client 3',
                adresa='Adresa 3',
                broj='3',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='client3@test.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            # Create faktura
            data = {
                'tip_fakture': 'standardna',
                'komitent_id': komitent.id,
                'datum_prometa': date.today(),
                'valuta_placanja': 7,
                'stavke': [
                    {
                        'naziv': 'Usluga',
                        'kolicina': Decimal('1.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('100.00')
                    }
                ]
            }
            faktura = create_faktura(data, user)

            # Change status to 'stornirana'
            faktura.status = 'stornirana'
            db.session.commit()

            # Try to update
            updated_data = {
                'tip_fakture': 'standardna',
                'komitent_id': komitent.id,
                'datum_prometa': date.today(),
                'valuta_placanja': 14,
                'stavke': [
                    {
                        'naziv': 'New Usluga',
                        'kolicina': Decimal('1.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('200.00')
                    }
                ]
            }

            with pytest.raises(ValueError) as exc_info:
                update_faktura(faktura.id, updated_data, user)

            assert "Cannot update faktura with status 'stornirana'" in str(exc_info.value)

    def test_update_faktura_recalculates_ukupan_iznos(self, app, pausalac_with_firma):
        """Test that update_faktura recalculates total amount correctly."""
        with app.app_context():
            user, firma = pausalac_with_firma

            # Create domestic komitent
            komitent = Komitent(
                firma_id=firma.id,
                pib='44444444',
                maticni_broj='44444444',
                naziv='Client 4',
                adresa='Adresa 4',
                broj='4',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='client4@test.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            # Create draft faktura with one stavka
            data = {
                'tip_fakture': 'standardna',
                'komitent_id': komitent.id,
                'datum_prometa': date.today(),
                'valuta_placanja': 7,
                'stavke': [
                    {
                        'naziv': 'Stavka 1',
                        'kolicina': Decimal('2.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('100.00')
                    }
                ]
            }
            faktura = create_faktura(data, user)
            assert faktura.ukupan_iznos_rsd == Decimal('200.00')

            # Update with multiple stavke
            updated_data = {
                'tip_fakture': 'standardna',
                'komitent_id': komitent.id,
                'datum_prometa': date.today(),
                'valuta_placanja': 7,
                'stavke': [
                    {
                        'naziv': 'Stavka A',
                        'kolicina': Decimal('3.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('150.00')
                    },
                    {
                        'naziv': 'Stavka B',
                        'kolicina': Decimal('5.00'),
                        'jedinica_mere': 'kom',
                        'cena': Decimal('50.00')
                    }
                ]
            }
            updated_faktura = update_faktura(faktura.id, updated_data, user)

            # 3 * 150 + 5 * 50 = 450 + 250 = 700
            assert updated_faktura.ukupan_iznos_rsd == Decimal('700.00')
            assert len(updated_faktura.stavke) == 2

    def test_update_faktura_recalculates_datum_dospeca(self, app, pausalac_with_firma):
        """Test that update_faktura recalculates due date with weekend adjustment."""
        with app.app_context():
            user, firma = pausalac_with_firma

            # Create domestic komitent
            komitent = Komitent(
                firma_id=firma.id,
                pib='55555555',
                maticni_broj='55555555',
                naziv='Client 5',
                adresa='Adresa 5',
                broj='5',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='client5@test.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            # Create draft faktura
            datum_prometa = date(2025, 11, 3)  # Monday
            data = {
                'tip_fakture': 'standardna',
                'komitent_id': komitent.id,
                'datum_prometa': datum_prometa,
                'valuta_placanja': 7,
                'stavke': [
                    {
                        'naziv': 'Usluga',
                        'kolicina': Decimal('1.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('100.00')
                    }
                ]
            }
            faktura = create_faktura(data, user)

            # datum_dospeca should be 7 days later: 2025-11-10 (Monday)
            expected_dospeca = date(2025, 11, 10)
            assert faktura.datum_dospeca == expected_dospeca

            # Update with new valuta_placanja
            updated_data = {
                'tip_fakture': 'standardna',
                'komitent_id': komitent.id,
                'datum_prometa': datum_prometa,
                'valuta_placanja': 14,  # Changed to 14 days
                'stavke': [
                    {
                        'naziv': 'Usluga',
                        'kolicina': Decimal('1.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('100.00')
                    }
                ]
            }
            updated_faktura = update_faktura(faktura.id, updated_data, user)

            # datum_dospeca should be 14 days later: 2025-11-17 (Monday)
            expected_dospeca_updated = date(2025, 11, 17)
            assert updated_faktura.datum_dospeca == expected_dospeca_updated


class TestProfakturaService:
    """Tests for profaktura-specific service logic (Story 4.1)."""

    def test_generate_broj_profakture(self, pausalac_with_firma):
        """Test that generate_broj_fakture generates number with PRO for profakture."""
        user, firma = pausalac_with_firma
        
        # Set brojac_profakture to 5
        firma.brojac_profakture = 5
        db.session.commit()
        
        broj = generate_broj_fakture(firma, tip_fakture='profaktura')
        
        # Should contain "PRO" and the counter
        assert 'PRO' in broj
        assert '0005' in broj

    def test_generate_broj_profakture_format(self, pausalac_with_firma):
        """Test that profaktura number format is {prefiks}PRO{brojac}{sufiks}."""
        user, firma = pausalac_with_firma
        
        # Set prefiks and sufiks
        firma.prefiks_fakture = 'MK-'
        firma.sufiks_fakture = '/2025-PS'
        firma.brojac_profakture = 1
        db.session.commit()
        
        broj = generate_broj_fakture(firma, tip_fakture='profaktura')
        
        # Should be: MK-PRO0001/2025-PS
        assert broj == 'MK-PRO0001/2025-PS'

    def test_create_profaktura_domestic(self, pausalac_with_firma, komitent):
        """Test creating domestic profaktura (RSD)."""
        user, firma = pausalac_with_firma
        
        data = {
            'tip_fakture': 'profaktura',
            'komitent_id': komitent.id,
            'datum_prometa': date.today(),
            'valuta_placanja': 7,
            'stavke': [
                {
                    'naziv': 'Konsultantske usluge',
                    'kolicina': Decimal('10.00'),
                    'jedinica_mere': 'h',
                    'cena': Decimal('5000.00')
                }
            ]
        }
        
        profaktura = create_faktura(data, user)
        
        assert profaktura.tip_fakture == 'profaktura'
        assert profaktura.valuta_fakture == 'RSD'
        assert profaktura.status == 'draft'
        assert profaktura.broj_fakture == f'DRAFT-{profaktura.id}'
        assert profaktura.ukupan_iznos_rsd == Decimal('50000.00')
        assert profaktura.jezik == 'sr'

    def test_finalize_profaktura_increments_brojac_profakture(self, pausalac_with_firma, komitent):
        """Test that finalizing profaktura increments brojac_profakture."""
        user, firma = pausalac_with_firma
        
        # Set initial profaktura brojac
        initial_brojac_profakture = 3
        firma.brojac_profakture = initial_brojac_profakture
        db.session.commit()
        
        # Create profaktura
        data = {
            'tip_fakture': 'profaktura',
            'komitent_id': komitent.id,
            'datum_prometa': date.today(),
            'valuta_placanja': 7,
            'stavke': [{'naziv': 'Usluga', 'kolicina': Decimal('1.00'), 'jedinica_mere': 'h', 'cena': Decimal('100.00')}]
        }
        profaktura = create_faktura(data, user)
        
        # Finalize profaktura
        finalized = finalize_faktura(profaktura.id)
        
        # Reload firma from DB
        db.session.refresh(firma)
        
        # Profaktura brojac should be incremented
        assert firma.brojac_profakture == initial_brojac_profakture + 1
        assert finalized.status == 'izdata'
        assert 'PRO' in finalized.broj_fakture

    def test_profaktura_and_standardna_have_separate_counters(self, pausalac_with_firma, komitent):
        """Test that profakture and standardne fakture have independent counters."""
        user, firma = pausalac_with_firma
        
        # Set initial brojaci
        firma.brojac_fakture = 10
        firma.brojac_profakture = 5
        db.session.commit()
        
        # Create and finalize standardna faktura
        data_standardna = {
            'tip_fakture': 'standardna',
            'komitent_id': komitent.id,
            'datum_prometa': date.today(),
            'valuta_placanja': 7,
            'stavke': [{'naziv': 'Usluga', 'kolicina': Decimal('1.00'), 'jedinica_mere': 'h', 'cena': Decimal('100.00')}]
        }
        standardna = create_faktura(data_standardna, user)
        finalize_faktura(standardna.id)
        
        db.session.refresh(firma)
        assert firma.brojac_fakture == 11
        assert firma.brojac_profakture == 5  # Should NOT change
        
        # Create and finalize profaktura
        data_profaktura = {
            'tip_fakture': 'profaktura',
            'komitent_id': komitent.id,
            'datum_prometa': date.today(),
            'valuta_placanja': 7,
            'stavke': [{'naziv': 'Usluga', 'kolicina': Decimal('1.00'), 'jedinica_mere': 'h', 'cena': Decimal('100.00')}]
        }
        profaktura = create_faktura(data_profaktura, user)
        finalize_faktura(profaktura.id)
        
        db.session.refresh(firma)
        assert firma.brojac_fakture == 11  # Should NOT change
        assert firma.brojac_profakture == 6  # Should increment


class TestAvansnaFakturaService:
    """Tests for avansna faktura service logic (Story 4.3)."""

    def test_generate_broj_fakture_avansna(self, pausalac_with_firma):
        """Test that generate_broj_fakture generates number with AVN for avansne fakture."""
        user, firma = pausalac_with_firma

        # Set brojac_avansne to 3
        firma.brojac_avansne = 3
        db.session.commit()

        broj = generate_broj_fakture(firma, tip_fakture='avansna')

        # Should contain "AVN" and the counter
        assert 'AVN' in broj
        assert '0003' in broj

    def test_generate_broj_avansna_format(self, pausalac_with_firma):
        """Test that avansna faktura number format is {prefiks}AVN{brojac}{sufiks}."""
        user, firma = pausalac_with_firma

        # Set prefiks and sufiks
        firma.prefiks_fakture = 'MK-'
        firma.sufiks_fakture = '/2025-PS'
        firma.brojac_avansne = 1
        db.session.commit()

        broj = generate_broj_fakture(firma, tip_fakture='avansna')

        # Should be: MK-AVN0001/2025-PS
        assert broj == 'MK-AVN0001/2025-PS'

    def test_create_avansna_faktura_with_procenat(self, pausalac_with_firma, komitent):
        """Test creating avansna faktura with procenat avansa (percentage)."""
        user, firma = pausalac_with_firma

        data = {
            'tip_fakture': 'avansna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 7),
            'valuta_placanja': 7,
            'ukupna_vrednost_posla': Decimal('10000.00'),
            'procenat_avansa': 30,
            'opis_posla': 'Projekat XYZ'
        }

        avansna = create_faktura(data, user)

        # Assertions
        assert avansna.tip_fakture == 'avansna'
        assert avansna.status == 'draft'
        assert avansna.broj_fakture == f'DRAFT-{avansna.id}'
        assert len(avansna.stavke) == 1  # Only one stavka
        assert avansna.stavke[0].naziv == 'Avans 30% za Projekat XYZ'
        assert avansna.stavke[0].kolicina == Decimal('1.00')
        assert avansna.stavke[0].cena == Decimal('3000.00')  # 30% of 10000
        assert avansna.stavke[0].ukupno == Decimal('3000.00')
        assert avansna.ukupan_iznos_rsd == Decimal('3000.00')
        assert avansna.valuta_fakture == 'RSD'
        assert avansna.jezik == 'sr'

    def test_create_avansna_faktura_without_procenat(self, pausalac_with_firma, komitent):
        """Test creating avansna faktura without percentage (direct amount entry)."""
        user, firma = pausalac_with_firma

        data = {
            'tip_fakture': 'avansna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 7),
            'valuta_placanja': 7,
            'stavke': [
                {
                    'naziv': 'Avans za projekat ABC',
                    'kolicina': Decimal('1.00'),
                    'jedinica_mere': 'kom',
                    'cena': Decimal('5000.00')
                }
            ]
        }

        avansna = create_faktura(data, user)

        # Assertions
        assert avansna.tip_fakture == 'avansna'
        assert avansna.status == 'draft'
        assert len(avansna.stavke) == 1
        assert avansna.stavke[0].naziv == 'Avans za projekat ABC'
        assert avansna.stavke[0].cena == Decimal('5000.00')
        assert avansna.ukupan_iznos_rsd == Decimal('5000.00')

    def test_create_avansna_faktura_procenat_requires_ukupna_vrednost(self, pausalac_with_firma, komitent):
        """Test that procenat avansa requires ukupna_vrednost_posla."""
        user, firma = pausalac_with_firma

        data = {
            'tip_fakture': 'avansna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 7),
            'valuta_placanja': 7,
            'procenat_avansa': 30,  # Percentage without ukupna_vrednost
            'opis_posla': 'Projekat XYZ'
        }

        with pytest.raises(ValueError) as exc_info:
            create_faktura(data, user)

        assert 'Ukupna vrednost posla je obavezna kada je procenat avansa unet' in str(exc_info.value)

    def test_finalize_avansna_increments_brojac_avansne(self, pausalac_with_firma, komitent):
        """Test that finalizing avansna faktura increments brojac_avansne."""
        user, firma = pausalac_with_firma

        # Set initial avansna brojac
        initial_brojac_avansne = 5
        firma.brojac_avansne = initial_brojac_avansne
        db.session.commit()

        # Create avansna faktura
        data = {
            'tip_fakture': 'avansna',
            'komitent_id': komitent.id,
            'datum_prometa': date.today(),
            'valuta_placanja': 7,
            'ukupna_vrednost_posla': Decimal('20000.00'),
            'procenat_avansa': 50,
            'opis_posla': 'Projekat DEF'
        }
        avansna = create_faktura(data, user)

        # Finalize avansna faktura
        finalized = finalize_faktura(avansna.id)

        # Reload firma from DB
        db.session.refresh(firma)

        # Avansna brojac should be incremented
        assert firma.brojac_avansne == initial_brojac_avansne + 1
        assert finalized.status == 'izdata'
        assert 'AVN' in finalized.broj_fakture

    def test_avansna_and_standardna_have_separate_counters(self, pausalac_with_firma, komitent):
        """Test that avansne fakture and standardne fakture have independent counters."""
        user, firma = pausalac_with_firma

        # Set initial brojaci
        firma.brojac_fakture = 10
        firma.brojac_avansne = 3
        db.session.commit()

        # Create and finalize standardna faktura
        data_standardna = {
            'tip_fakture': 'standardna',
            'komitent_id': komitent.id,
            'datum_prometa': date.today(),
            'valuta_placanja': 7,
            'stavke': [{'naziv': 'Usluga', 'kolicina': Decimal('1.00'), 'jedinica_mere': 'h', 'cena': Decimal('100.00')}]
        }
        standardna = create_faktura(data_standardna, user)
        finalize_faktura(standardna.id)

        db.session.refresh(firma)
        assert firma.brojac_fakture == 11
        assert firma.brojac_avansne == 3  # Should NOT change

        # Create and finalize avansna faktura
        data_avansna = {
            'tip_fakture': 'avansna',
            'komitent_id': komitent.id,
            'datum_prometa': date.today(),
            'valuta_placanja': 7,
            'ukupna_vrednost_posla': Decimal('5000.00'),
            'procenat_avansa': 40,
            'opis_posla': 'Projekat GHI'
        }
        avansna = create_faktura(data_avansna, user)
        finalize_faktura(avansna.id)

        db.session.refresh(firma)
        assert firma.brojac_fakture == 11  # Should NOT change
        assert firma.brojac_avansne == 4  # Should increment

    def test_create_avansna_faktura_calculates_iznos_correctly(self, pausalac_with_firma, komitent):
        """Test that avansna faktura calculates iznos correctly from percentage."""
        user, firma = pausalac_with_firma

        test_cases = [
            # (ukupna_vrednost, procenat, expected_iznos)
            (Decimal('10000.00'), 30, Decimal('3000.00')),
            (Decimal('15000.00'), 50, Decimal('7500.00')),
            (Decimal('8500.00'), 25, Decimal('2125.00')),
            (Decimal('100000.00'), 10, Decimal('10000.00')),
        ]

        for ukupna, procenat, expected in test_cases:
            data = {
                'tip_fakture': 'avansna',
                'komitent_id': komitent.id,
                'datum_prometa': date.today(),
                'valuta_placanja': 7,
                'ukupna_vrednost_posla': ukupna,
                'procenat_avansa': procenat,
                'opis_posla': f'Test {procenat}%'
            }

            avansna = create_faktura(data, user)

            assert avansna.ukupan_iznos_rsd == expected
            assert avansna.stavke[0].ukupno == expected

            # Cleanup for next iteration
            db.session.delete(avansna)
            db.session.commit()


class TestZatvaranjeAvansa:
    """Tests for closing avansna faktura (Story 4.4)."""

    def test_create_faktura_with_avans_odbitak(self, pausalac_with_firma, komitent, db):
        """Test creating faktura that closes an avans."""
        user, firma = pausalac_with_firma

        # First, create and finalize avansna faktura
        avansna_data = {
            'tip_fakture': 'avansna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 7),
            'valuta_placanja': 7,
            'ukupna_vrednost_posla': Decimal('10000.00'),
            'procenat_avansa': 30,
            'opis_posla': 'Projekat XYZ',
            'stavke': []
        }
        avansna = create_faktura(avansna_data, user)
        finalize_faktura(avansna.id)
        db.session.commit()

        # Now create final faktura that closes the avans
        faktura_data = {
            'tip_fakture': 'standardna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 8),
            'valuta_placanja': 7,
            'zatvara_avans': True,
            'avansna_faktura_id': avansna.id,
            'stavke': [
                {
                    'naziv': 'Usluga 1',
                    'kolicina': Decimal('10.00'),
                    'jedinica_mere': 'h',
                    'cena': Decimal('500.00'),
                    'ukupno': Decimal('5000.00')
                }
            ]
        }

        faktura = create_faktura(faktura_data, user)

        # Assertions
        assert faktura.avansna_faktura_id == avansna.id
        assert len(faktura.stavke) == 2  # Regular stavka + avans odbitak

    def test_avans_odbitak_adds_negative_stavka(self, pausalac_with_firma, komitent, db):
        """Test that avans odbitak adds a negative stavka with correct name."""
        user, firma = pausalac_with_firma

        # Create and finalize avansna faktura
        avansna_data = {
            'tip_fakture': 'avansna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 7),
            'valuta_placanja': 7,
            'ukupna_vrednost_posla': Decimal('10000.00'),
            'procenat_avansa': 30,
            'opis_posla': 'Projekat ABC'
        }
        avansna = create_faktura(avansna_data, user)
        finalize_faktura(avansna.id)
        db.session.commit()

        # Create final faktura that closes the avans
        faktura_data = {
            'tip_fakture': 'standardna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 8),
            'valuta_placanja': 7,
            'zatvara_avans': True,
            'avansna_faktura_id': avansna.id,
            'stavke': [{'naziv': 'Usluga', 'kolicina': Decimal('1'), 'jedinica_mere': 'kom', 'cena': Decimal('5000.00')}]
        }

        faktura = create_faktura(faktura_data, user)

        # Find odbitak stavka
        odbitak = [s for s in faktura.stavke if 'Odbitak avansa' in s.naziv][0]
        assert f"Odbitak avansa - {avansna.broj_fakture}" in odbitak.naziv
        assert odbitak.cena < 0  # Negative
        assert odbitak.ukupno < 0  # Negative

    def test_avans_odbitak_calculates_correct_total(self, pausalac_with_firma, komitent, db):
        """Test that total amount is calculated correctly (sum - avans)."""
        user, firma = pausalac_with_firma

        # Create and finalize avansna faktura (3000 RSD)
        avansna_data = {
            'tip_fakture': 'avansna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 7),
            'valuta_placanja': 7,
            'ukupna_vrednost_posla': Decimal('10000.00'),
            'procenat_avansa': 30
        }
        avansna = create_faktura(avansna_data, user)
        finalize_faktura(avansna.id)
        db.session.commit()

        # Create final faktura (5000 RSD - 3000 RSD avans = 2000 RSD)
        faktura_data = {
            'tip_fakture': 'standardna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 8),
            'valuta_placanja': 7,
            'zatvara_avans': True,
            'avansna_faktura_id': avansna.id,
            'stavke': [{'naziv': 'Usluga', 'kolicina': Decimal('1'), 'jedinica_mere': 'kom', 'cena': Decimal('5000.00')}]
        }

        faktura = create_faktura(faktura_data, user)

        # Total should be 5000 - 3000 = 2000
        assert faktura.ukupan_iznos_rsd == Decimal('2000.00')

    def test_cannot_close_already_closed_avans(self, pausalac_with_firma, komitent, db):
        """Test that already closed avans cannot be closed again."""
        user, firma = pausalac_with_firma

        # Create and finalize avansna faktura
        avansna_data = {
            'tip_fakture': 'avansna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 7),
            'valuta_placanja': 7,
            'ukupna_vrednost_posla': Decimal('10000.00'),
            'procenat_avansa': 30
        }
        avansna = create_faktura(avansna_data, user)
        finalize_faktura(avansna.id)

        # Close it once
        faktura1_data = {
            'tip_fakture': 'standardna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 8),
            'valuta_placanja': 7,
            'zatvara_avans': True,
            'avansna_faktura_id': avansna.id,
            'stavke': [{'naziv': 'Usluga', 'kolicina': Decimal('1'), 'jedinica_mere': 'kom', 'cena': Decimal('5000.00')}]
        }
        faktura1 = create_faktura(faktura1_data, user)
        finalize_faktura(faktura1.id)
        db.session.commit()

        # Try to close it again - should raise ValueError
        faktura2_data = {
            'tip_fakture': 'standardna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 9),
            'valuta_placanja': 7,
            'zatvara_avans': True,
            'avansna_faktura_id': avansna.id,
            'stavke': [{'naziv': 'Usluga', 'kolicina': Decimal('1'), 'jedinica_mere': 'kom', 'cena': Decimal('2000.00')}]
        }

        with pytest.raises(ValueError, match="već zatvorena"):
            create_faktura(faktura2_data, user)

    def test_cannot_close_avans_if_total_negative(self, pausalac_with_firma, komitent, db):
        """Test that total cannot be negative (avans > total value)."""
        user, firma = pausalac_with_firma

        # Create and finalize avansna faktura (5000 RSD)
        avansna_data = {
            'tip_fakture': 'avansna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 7),
            'valuta_placanja': 7,
            'ukupna_vrednost_posla': Decimal('10000.00'),
            'procenat_avansa': 50
        }
        avansna = create_faktura(avansna_data, user)
        finalize_faktura(avansna.id)
        db.session.commit()

        # Try to create faktura where avans (5000) > work value (3000)
        faktura_data = {
            'tip_fakture': 'standardna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 8),
            'valuta_placanja': 7,
            'zatvara_avans': True,
            'avansna_faktura_id': avansna.id,
            'stavke': [{'naziv': 'Usluga', 'kolicina': Decimal('1'), 'jedinica_mere': 'kom', 'cena': Decimal('3000.00')}]
        }

        with pytest.raises(ValueError, match="ne može biti negativan"):
            create_faktura(faktura_data, user)

    def test_close_avans_updates_status(self, pausalac_with_firma, komitent, db):
        """Test that avansna faktura status changes to 'zatvorena'."""
        from app.services.faktura_service import close_avans_faktura

        user, firma = pausalac_with_firma

        # Create and finalize avansna faktura
        avansna_data = {
            'tip_fakture': 'avansna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 7),
            'valuta_placanja': 7,
            'ukupna_vrednost_posla': Decimal('10000.00'),
            'procenat_avansa': 30
        }
        avansna = create_faktura(avansna_data, user)
        finalize_faktura(avansna.id)
        db.session.commit()

        # Create final faktura
        faktura_data = {
            'tip_fakture': 'standardna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 8),
            'valuta_placanja': 7,
            'stavke': [{'naziv': 'Usluga', 'kolicina': Decimal('1'), 'jedinica_mere': 'kom', 'cena': Decimal('5000.00')}]
        }
        faktura = create_faktura(faktura_data, user)
        db.session.commit()

        # Close avans
        close_avans_faktura(avansna.id, faktura.id)
        db.session.commit()

        # Refresh avansna from DB
        db.session.refresh(avansna)
        assert avansna.status == 'zatvorena'

    def test_close_avans_creates_bidirectional_link(self, pausalac_with_firma, komitent, db):
        """Test bidirectional linking between avansna and final faktura."""
        from app.services.faktura_service import close_avans_faktura

        user, firma = pausalac_with_firma

        # Create and finalize avansna faktura
        avansna_data = {
            'tip_fakture': 'avansna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 7),
            'valuta_placanja': 7,
            'ukupna_vrednost_posla': Decimal('10000.00'),
            'procenat_avansa': 30
        }
        avansna = create_faktura(avansna_data, user)
        finalize_faktura(avansna.id)
        db.session.commit()

        # Create final faktura
        faktura_data = {
            'tip_fakture': 'standardna',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 8),
            'valuta_placanja': 7,
            'stavke': [{'naziv': 'Usluga', 'kolicina': Decimal('1'), 'jedinica_mere': 'kom', 'cena': Decimal('5000.00')}]
        }
        faktura = create_faktura(faktura_data, user)
        db.session.commit()

        # Close avans
        close_avans_faktura(avansna.id, faktura.id)
        db.session.commit()

        # Refresh from DB
        db.session.refresh(avansna)

        # Check bidirectional link
        assert avansna.konvertovana_u_fakturu_id == faktura.id
