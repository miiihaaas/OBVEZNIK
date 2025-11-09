"""Unit tests for SQLAlchemy models."""
import pytest
from datetime import date, datetime
from decimal import Decimal

from app import db
from app.models import (
    User,
    PausalnFirma,
    Komitent,
    Artikal,
    Faktura,
    FakturaStavka,
    Memorandum,
    KPOEntry,
)


class TestUserModel:
    """Tests for User model."""

    def test_user_model_creation(self, app):
        """Test User model can be created with required fields."""
        with app.app_context():
            user = User(
                email='test@example.com',
                password_hash='hashed_password_123',
                full_name='Test User',
                role='pausalac'
            )
            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.email == 'test@example.com'
            assert user.password_hash == 'hashed_password_123'
            assert user.full_name == 'Test User'
            assert user.role == 'pausalac'
            assert user.is_active is True
            assert user.firma_id is None
            assert user.created_at is not None
            assert user.last_login is None

    def test_user_is_admin_method(self, app):
        """Test is_admin() returns correct boolean value."""
        with app.app_context():
            admin = User(
                email='admin@example.com',
                password_hash='hash',
                full_name='Admin User',
                role='admin'
            )
            pausalac = User(
                email='pausalac@example.com',
                password_hash='hash',
                full_name='Pausalac User',
                role='pausalac'
            )

            assert admin.is_admin() is True
            assert pausalac.is_admin() is False

    def test_user_relationships(self, app):
        """Test User relationships with PausalnFirma and Faktura."""
        with app.app_context():
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test Adresa',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='0111234567',
                email='test@firma.rs',
                dinarski_racuni=[{'racun': '160-123456-78', 'banka': 'Test Banka'}],
            )
            db.session.add(firma)
            db.session.commit()

            user = User(
                email='user@example.com',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            assert user.firma is not None
            assert user.firma.naziv == 'Test Firma'
            assert user in firma.users


class TestPausalnFirmaModel:
    """Tests for PausalnFirma model."""

    def test_firma_model_creation(self, app):
        """Test PausalnFirma model can be created with required fields."""
        with app.app_context():
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma d.o.o.',
                adresa='Kneza Miloša',
                broj='10',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='0111234567',
                email='info@testfirma.rs',
                dinarski_racuni=[
                    {'racun': '160-123456-78', 'banka': 'Banka Intesa'},
                    {'racun': '170-987654-32', 'banka': 'Komercijalna Banka'}
                ],
                devizni_racuni=[
                    {'racun': 'RS35160005050123456789', 'valuta': 'EUR'}
                ]
            )
            db.session.add(firma)
            db.session.commit()

            assert firma.id is not None
            assert firma.pib == '12345678'
            assert firma.maticni_broj == '87654321'
            assert firma.naziv == 'Test Firma d.o.o.'
            assert firma.brojac_fakture == 1
            assert firma.brojac_profakture == 1
            assert firma.pdv_kategorija == 'SS'
            assert firma.sifra_osnova == 'PDV-RS-33'
            assert firma.is_active is True
            assert firma.created_at is not None
            assert len(firma.dinarski_racuni) == 2
            assert len(firma.devizni_racuni) == 1

    def test_get_next_broj_fakture_with_prefix_suffix(self, app):
        """Test invoice number generation with prefix and suffix."""
        with app.app_context():
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[],
                prefiks_fakture='INV-',
                sufiks_fakture='/2025',
                brojac_fakture=42
            )

            assert firma.get_next_broj_fakture() == 'INV-42/2025'

    def test_get_next_broj_fakture_without_prefix_suffix(self, app):
        """Test invoice number generation without prefix and suffix."""
        with app.app_context():
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[],
                brojac_fakture=10
            )

            assert firma.get_next_broj_fakture() == '10'

    def test_firma_relationships(self, app):
        """Test PausalnFirma relationships with other models."""
        with app.app_context():
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            # Test relationships exist
            assert firma.users == []
            assert firma.komitenti == []
            assert firma.artikli == []
            assert firma.fakture == []


class TestKomitentModel:
    """Tests for Komitent model."""

    def test_komitent_model_creation(self, app):
        """Test Komitent model can be created with required fields."""
        with app.app_context():
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id,
                pib='98765432',
                maticni_broj='12348765',
                naziv='Komitent d.o.o.',
                adresa='Njegoševa',
                broj='15',
                postanski_broj='21000',
                mesto='Novi Sad',
                drzava='Srbija',
                email='kontakt@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            assert komitent.id is not None
            assert komitent.firma_id == firma.id
            assert komitent.pib == '98765432'
            assert komitent.naziv == 'Komitent d.o.o.'
            assert komitent.created_at is not None

    def test_komitent_tenant_isolation(self, app):
        """Test that komitenti are properly isolated by firma_id."""
        with app.app_context():
            firma1 = PausalnFirma(
                pib='11111111',
                maticni_broj='11111111',
                naziv='Firma 1',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011111111',
                email='firma1@test.rs',
                dinarski_racuni=[]
            )
            firma2 = PausalnFirma(
                pib='22222222',
                maticni_broj='22222222',
                naziv='Firma 2',
                adresa='Test',
                broj='2',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='022222222',
                email='firma2@test.rs',
                dinarski_racuni=[]
            )
            db.session.add_all([firma1, firma2])
            db.session.commit()

            komitent1 = Komitent(
                firma_id=firma1.id,
                pib='99999999',
                maticni_broj='99999999',
                naziv='Komitent 1',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='k1@test.rs'
            )
            komitent2 = Komitent(
                firma_id=firma2.id,
                pib='88888888',
                maticni_broj='88888888',
                naziv='Komitent 2',
                adresa='Test',
                broj='2',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='k2@test.rs'
            )
            db.session.add_all([komitent1, komitent2])
            db.session.commit()

            # Each firma should see only their own komitenti
            assert len(firma1.komitenti) == 1
            assert len(firma2.komitenti) == 1
            assert firma1.komitenti[0].naziv == 'Komitent 1'
            assert firma2.komitenti[0].naziv == 'Komitent 2'

    def test_komitent_with_devizni_racuni(self, app):
        """Test Komitent can be created with devizni računi."""
        with app.app_context():
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id,
                pib='98765432',
                maticni_broj='12348765',
                naziv='Foreign Komitent Ltd.',
                adresa='Main Street',
                broj='100',
                postanski_broj='10000',
                mesto='Berlin',
                drzava='Germany',
                email='contact@foreignkomitent.com',
                devizni_racuni=[{
                    'banka': 'Deutsche Bank',
                    'iban': 'DE89370400440532013000',
                    'swift': 'COBADEFFXXX',
                    'valuta': 'EUR'
                }]
            )
            db.session.add(komitent)
            db.session.commit()

            assert komitent.id is not None
            assert komitent.devizni_racuni is not None
            assert len(komitent.devizni_racuni) == 1
            assert komitent.devizni_racuni[0]['iban'] == 'DE89370400440532013000'
            assert komitent.devizni_racuni[0]['swift'] == 'COBADEFFXXX'
            assert komitent.devizni_racuni[0]['valuta'] == 'EUR'

    def test_komitent_devizni_racuni_optional_for_domestic(self, app):
        """Test devizni računi are optional for domestic komitenti."""
        with app.app_context():
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id,
                pib='98765432',
                maticni_broj='12348765',
                naziv='Domestic Komitent d.o.o.',
                adresa='Njegoševa',
                broj='15',
                postanski_broj='21000',
                mesto='Novi Sad',
                drzava='Srbija',
                email='kontakt@domestic.rs'
                # devizni_racuni not provided
            )
            db.session.add(komitent)
            db.session.commit()

            assert komitent.id is not None
            assert komitent.devizni_racuni is None


class TestArtikalModel:
    """Tests for Artikal model."""

    def test_artikal_model_creation(self, app):
        """Test Artikal model can be created with required fields."""
        with app.app_context():
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            artikal = Artikal(
                firma_id=firma.id,
                naziv='Softverske usluge',
                opis='Razvoj web aplikacija',
                podrazumevana_cena=Decimal('5000.00'),
                jedinica_mere='sat'
            )
            db.session.add(artikal)
            db.session.commit()

            assert artikal.id is not None
            assert artikal.firma_id == firma.id
            assert artikal.naziv == 'Softverske usluge'
            assert artikal.opis == 'Razvoj web aplikacija'
            assert artikal.podrazumevana_cena == Decimal('5000.00')
            assert artikal.jedinica_mere == 'sat'
            assert artikal.created_at is not None

    def test_artikal_tenant_isolation(self, app):
        """Test that artikli are properly isolated by firma_id."""
        with app.app_context():
            firma1 = PausalnFirma(
                pib='11111111',
                maticni_broj='11111111',
                naziv='Firma 1',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011111111',
                email='firma1@test.rs',
                dinarski_racuni=[]
            )
            firma2 = PausalnFirma(
                pib='22222222',
                maticni_broj='22222222',
                naziv='Firma 2',
                adresa='Test',
                broj='2',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='022222222',
                email='firma2@test.rs',
                dinarski_racuni=[]
            )
            db.session.add_all([firma1, firma2])
            db.session.commit()

            artikal1 = Artikal(
                firma_id=firma1.id,
                naziv='Usluga 1',
                jedinica_mere='kom'
            )
            artikal2 = Artikal(
                firma_id=firma2.id,
                naziv='Usluga 2',
                jedinica_mere='kom'
            )
            db.session.add_all([artikal1, artikal2])
            db.session.commit()

            # Each firma should see only their own artikli
            assert len(firma1.artikli) == 1
            assert len(firma2.artikli) == 1
            assert firma1.artikli[0].naziv == 'Usluga 1'
            assert firma2.artikli[0].naziv == 'Usluga 2'


class TestFakturaModel:
    """Tests for Faktura model."""

    def test_faktura_model_creation(self, app):
        """Test Faktura model can be created with required fields."""
        with app.app_context():
            # Create dependencies
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id,
                pib='98765432',
                maticni_broj='12348765',
                naziv='Komitent',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='k@test.rs'
            )
            db.session.add(komitent)

            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create faktura
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='001/2025',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                jezik='sr',
                datum_prometa=date(2025, 10, 12),
                valuta_placanja=30,
                datum_dospeca=date(2025, 11, 11),
                ukupan_iznos_rsd=Decimal('120000.00'),
                status='draft'
            )
            db.session.add(faktura)
            db.session.commit()

            assert faktura.id is not None
            assert faktura.broj_fakture == '001/2025'
            assert faktura.tip_fakture == 'standardna'
            assert faktura.valuta_fakture == 'RSD'
            assert faktura.status == 'draft'
            assert faktura.ukupan_iznos_rsd == Decimal('120000.00')

    def test_calculate_datum_dospeca(self, app):
        """Test Faktura calculates due date correctly."""
        with app.app_context():
            faktura = Faktura(
                datum_prometa=date(2025, 10, 12),
                valuta_placanja=30
            )
            faktura.calculate_datum_dospeca()
            assert faktura.datum_dospeca == date(2025, 11, 11)

    def test_faktura_unique_constraint(self, app):
        """Test unique constraint on (firma_id, broj_fakture)."""
        with app.app_context():
            # Create dependencies
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id,
                pib='98765432',
                maticni_broj='12348765',
                naziv='Komitent',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='k@test.rs'
            )
            db.session.add(komitent)

            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create first faktura
            faktura1 = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='001/2025',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 10, 12),
                valuta_placanja=30,
                datum_dospeca=date(2025, 11, 11),
                ukupan_iznos_rsd=Decimal('100.00')
            )
            db.session.add(faktura1)
            db.session.commit()

            # Try to create duplicate
            faktura2 = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='001/2025',  # Same broj_fakture
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 10, 12),
                valuta_placanja=30,
                datum_dospeca=date(2025, 11, 11),
                ukupan_iznos_rsd=Decimal('200.00')
            )
            db.session.add(faktura2)

            # Should raise IntegrityError
            with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
                db.session.commit()

    def test_faktura_pdf_status_default(self, app):
        """Test Faktura can be created with default status_pdf = 'pending'."""
        with app.app_context():
            # Create dependencies
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id,
                pib='98765432',
                maticni_broj='12348765',
                naziv='Komitent',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='k@test.rs'
            )
            db.session.add(komitent)

            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create faktura without specifying status_pdf
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='001/2025',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 10, 12),
                valuta_placanja=30,
                datum_dospeca=date(2025, 11, 11),
                ukupan_iznos_rsd=Decimal('100.00')
            )
            db.session.add(faktura)
            db.session.commit()

            # Should default to 'pending'
            assert faktura.status_pdf == 'pending'
            assert faktura.pdf_url is None

    def test_faktura_pdf_url_nullable(self, app):
        """Test pdf_url can be NULL or string path."""
        with app.app_context():
            # Create dependencies
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id,
                pib='98765432',
                maticni_broj='12348765',
                naziv='Komitent',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='k@test.rs'
            )
            db.session.add(komitent)

            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create faktura with pdf_url
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='001/2025',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 10, 12),
                valuta_placanja=30,
                datum_dospeca=date(2025, 11, 11),
                ukupan_iznos_rsd=Decimal('100.00'),
                pdf_url='storage/fakture/1/2025/01/001-2025.pdf',
                status_pdf='generated'
            )
            db.session.add(faktura)
            db.session.commit()

            assert faktura.pdf_url == 'storage/fakture/1/2025/01/001-2025.pdf'
            assert faktura.status_pdf == 'generated'


class TestFakturaStavkaModel:
    """Tests for FakturaStavka model."""

    def test_stavka_model_creation(self, app):
        """Test FakturaStavka model can be created with required fields."""
        with app.app_context():
            # Create dependencies
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            artikal = Artikal(
                firma_id=firma.id,
                naziv='Test Usluga',
                jedinica_mere='sat'
            )
            db.session.add(artikal)

            komitent = Komitent(
                firma_id=firma.id,
                pib='98765432',
                maticni_broj='12348765',
                naziv='Komitent',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='k@test.rs'
            )
            db.session.add(komitent)

            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='001/2025',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 10, 12),
                valuta_placanja=30,
                datum_dospeca=date(2025, 11, 11),
                ukupan_iznos_rsd=Decimal('5000.00')
            )
            db.session.add(faktura)
            db.session.commit()

            # Create faktura stavka
            stavka = FakturaStavka(
                faktura_id=faktura.id,
                artikal_id=artikal.id,
                naziv='Softverske usluge',
                kolicina=Decimal('10.00'),
                jedinica_mere='sat',
                cena=Decimal('5000.00'),
                ukupno=Decimal('50000.00'),
                redni_broj=1
            )
            db.session.add(stavka)
            db.session.commit()

            assert stavka.id is not None
            assert stavka.faktura_id == faktura.id
            assert stavka.artikal_id == artikal.id
            assert stavka.naziv == 'Softverske usluge'
            assert stavka.kolicina == Decimal('10.00')
            assert stavka.cena == Decimal('5000.00')
            assert stavka.ukupno == Decimal('50000.00')

    def test_calculate_ukupno(self, app):
        """Test FakturaStavka calculates total correctly."""
        with app.app_context():
            stavka = FakturaStavka(
                kolicina=Decimal('5.00'),
                cena=Decimal('1000.00')
            )
            stavka.calculate_ukupno()
            assert stavka.ukupno == Decimal('5000.00')


class TestMemorandumModel:
    """Tests for Memorandum model (placeholder)."""

    def test_memorandum_model_creation(self, app):
        """Test Memorandum model can be created with basic fields."""
        with app.app_context():
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            memorandum = Memorandum(
                firma_id=firma.id
            )
            db.session.add(memorandum)
            db.session.commit()

            assert memorandum.id is not None
            assert memorandum.firma_id == firma.id
            assert memorandum.created_at is not None


class TestCascadeDeletes:
    """Tests for foreign key cascade delete behavior."""

    def test_cascade_delete_firma(self, app):
        """Test that deleting firma cascades to related records."""
        with app.app_context():
            # Create firma with all related records
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id,
                pib='98765432',
                maticni_broj='12348765',
                naziv='Komitent',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='k@test.rs'
            )
            db.session.add(komitent)

            artikal = Artikal(
                firma_id=firma.id,
                naziv='Test Artikal',
                jedinica_mere='kom'
            )
            db.session.add(artikal)

            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='001/2025',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 10, 12),
                valuta_placanja=30,
                datum_dospeca=date(2025, 11, 11),
                ukupan_iznos_rsd=Decimal('100.00')
            )
            db.session.add(faktura)
            db.session.commit()

            firma_id = firma.id
            komitent_id = komitent.id
            artikal_id = artikal.id
            faktura_id = faktura.id

            # Delete firma
            db.session.delete(firma)
            db.session.commit()

            # All related records should be deleted (cascade)
            assert db.session.get(Komitent, komitent_id) is None
            assert db.session.get(Artikal, artikal_id) is None
            assert db.session.get(Faktura, faktura_id) is None

            # User should still exist but firma_id should be NULL
            user_after = db.session.get(User, user.id)
            assert user_after is not None
            assert user_after.firma_id is None


class TestMemorandumModel:
    """Tests for Memorandum model."""

    def test_memorandum_creation(self, app):
        """Test Memorandum model can be created with required fields."""
        with app.app_context():
            # Create firma dependency
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            # Create memorandum
            memo = Memorandum(
                firma_id=firma.id,
                naslov='Testni memorandum',
                sadrzaj='Ovo je sadrzaj testnog memoranduma sa dovoljno karaktera.',
                datum=date(2025, 11, 9)
            )
            db.session.add(memo)
            db.session.commit()

            assert memo.id is not None
            assert memo.firma_id == firma.id
            assert memo.naslov == 'Testni memorandum'
            assert memo.sadrzaj == 'Ovo je sadrzaj testnog memoranduma sa dovoljno karaktera.'
            assert memo.datum == date(2025, 11, 9)
            assert memo.komitent_id is None
            assert memo.faktura_id is None
            assert memo.created_at is not None

    def test_memorandum_with_komitent(self, app):
        """Test Memorandum can be linked to a Komitent."""
        with app.app_context():
            # Create dependencies
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id,
                pib='98765432',
                maticni_broj='12348765',
                naziv='Test Komitent',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='k@test.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            # Create memorandum with komitent link
            memo = Memorandum(
                firma_id=firma.id,
                naslov='Memorandum sa komitentom',
                sadrzaj='Ovaj memorandum je povezan sa komitentom za evidenciju sastanka.',
                datum=date.today(),
                komitent_id=komitent.id
            )
            db.session.add(memo)
            db.session.commit()

            assert memo.id is not None
            assert memo.komitent_id == komitent.id
            assert memo.komitent is not None
            assert memo.komitent.naziv == 'Test Komitent'

    def test_memorandum_with_faktura(self, app):
        """Test Memorandum can be linked to a Faktura."""
        with app.app_context():
            # Create dependencies
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id,
                pib='98765432',
                maticni_broj='12348765',
                naziv='Test Komitent',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='k@test.rs'
            )
            db.session.add(komitent)

            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='001/2025',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                jezik='sr',
                datum_prometa=date(2025, 10, 12),
                valuta_placanja=30,
                datum_dospeca=date(2025, 11, 11),
                ukupan_iznos_rsd=Decimal('120000.00'),
                status='draft'
            )
            db.session.add(faktura)
            db.session.commit()

            # Create memorandum with faktura link
            memo = Memorandum(
                firma_id=firma.id,
                naslov='Memorandum sa fakturom',
                sadrzaj='Ovaj memorandum je povezan sa fakturom radi evidencije placanja.',
                datum=date.today(),
                faktura_id=faktura.id
            )
            db.session.add(memo)
            db.session.commit()

            assert memo.id is not None
            assert memo.faktura_id == faktura.id
            assert memo.faktura is not None
            assert memo.faktura.broj_fakture == '001/2025'

    def test_memorandum_repr(self, app):
        """Test Memorandum __repr__ method returns expected string."""
        with app.app_context():
            # Create firma dependency
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            # Create memorandum with long title
            memo = Memorandum(
                firma_id=firma.id,
                naslov='Jako dugacak naslov memoranduma koji ima vise od 50 karaktera za testiranje truncate funkcionalnosti',
                sadrzaj='Sadrzaj memoranduma',
                datum=date.today()
            )
            db.session.add(memo)
            db.session.commit()

            # __repr__ should truncate naslov to first 50 chars
            expected = '<Memorandum Jako dugacak naslov memoranduma koji ima vise od 5>'
            assert repr(memo) == expected


class TestKPOEntryModel:
    """Tests for KPOEntry model."""

    def test_kpo_entry_creation(self, app):
        """Test KPOEntry model can be created with required fields."""
        with app.app_context():
            # Create firma
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            # Create komitent
            komitent = Komitent(
                firma_id=firma.id,
                naziv='Komitent d.o.o.',
                pib='87654321',
                maticni_broj='12345678',
                adresa='Adresa 1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='kontakt@komitent.rs',
                broj='1'
            )
            db.session.add(komitent)
            db.session.commit()

            # Create user
            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create faktura
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='F-2025-001',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 15),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 14),
                ukupan_iznos_rsd=Decimal('12000.00'),
                status='izdata',
                finalized_at=datetime.now()
            )
            db.session.add(faktura)
            db.session.commit()

            # Create KPO entry
            kpo_entry = KPOEntry(
                firma_id=firma.id,
                faktura_id=faktura.id,
                redni_broj=1,
                broj_fakture='F-2025-001',
                datum_prometa=date(2025, 1, 15),
                datum_dospeca=date(2025, 2, 14),
                komitent_naziv='Komitent d.o.o.',
                komitent_pib='87654321',
                opis='Usluge konsaltinga',
                iznos_rsd=Decimal('12000.00'),
                valuta='RSD',
                status_fakture='izdata',
                godina=2025
            )
            db.session.add(kpo_entry)
            db.session.commit()

            assert kpo_entry.id is not None
            assert kpo_entry.firma_id == firma.id
            assert kpo_entry.faktura_id == faktura.id
            assert kpo_entry.redni_broj == 1
            assert kpo_entry.broj_fakture == 'F-2025-001'
            assert kpo_entry.datum_prometa == date(2025, 1, 15)
            assert kpo_entry.datum_dospeca == date(2025, 2, 14)
            assert kpo_entry.komitent_naziv == 'Komitent d.o.o.'
            assert kpo_entry.komitent_pib == '87654321'
            assert kpo_entry.opis == 'Usluge konsaltinga'
            assert kpo_entry.iznos_rsd == Decimal('12000.00')
            assert kpo_entry.valuta == 'RSD'
            assert kpo_entry.status_fakture == 'izdata'
            assert kpo_entry.godina == 2025
            assert kpo_entry.created_at is not None

    def test_kpo_entry_unique_redni_broj_per_firma_godina(self, app):
        """Test unique constraint on redni_broj per firma and godina."""
        with app.app_context():
            # Create firma
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            # Create komitent
            komitent = Komitent(
                firma_id=firma.id,
                naziv='Komitent d.o.o.',
                pib='87654321',
                maticni_broj='12345678',
                adresa='Adresa 1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='kontakt@komitent.rs',
                broj='1'
            )
            db.session.add(komitent)
            db.session.commit()

            # Create user
            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create two fakturas
            faktura1 = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='F-2025-001',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 15),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 14),
                ukupan_iznos_rsd=Decimal('12000.00'),
                status='izdata'
            )
            db.session.add(faktura1)

            faktura2 = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='F-2025-002',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 16),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 15),
                ukupan_iznos_rsd=Decimal('15000.00'),
                status='izdata'
            )
            db.session.add(faktura2)
            db.session.commit()

            # Create first KPO entry
            kpo_entry1 = KPOEntry(
                firma_id=firma.id,
                faktura_id=faktura1.id,
                redni_broj=1,
                broj_fakture='F-2025-001',
                datum_prometa=date(2025, 1, 15),
                datum_dospeca=date(2025, 2, 14),
                komitent_naziv='Komitent d.o.o.',
                komitent_pib='87654321',
                opis='Test',
                iznos_rsd=Decimal('12000.00'),
                valuta='RSD',
                status_fakture='izdata',
                godina=2025
            )
            db.session.add(kpo_entry1)
            db.session.commit()

            # Attempt to create second KPO entry with same redni_broj, firma_id, and godina
            # This should raise IntegrityError due to unique constraint
            kpo_entry2 = KPOEntry(
                firma_id=firma.id,
                faktura_id=faktura2.id,
                redni_broj=1,  # Same redni_broj
                broj_fakture='F-2025-002',
                datum_prometa=date(2025, 1, 16),
                datum_dospeca=date(2025, 2, 15),
                komitent_naziv='Komitent d.o.o.',
                komitent_pib='87654321',
                opis='Test 2',
                iznos_rsd=Decimal('15000.00'),
                valuta='RSD',
                status_fakture='izdata',
                godina=2025  # Same godina
            )
            db.session.add(kpo_entry2)

            # Expect IntegrityError
            from sqlalchemy.exc import IntegrityError
            with pytest.raises(IntegrityError):
                db.session.commit()

            db.session.rollback()

    def test_kpo_entry_repr(self, app):
        """Test __repr__ method of KPOEntry."""
        with app.app_context():
            # Create firma
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            # Create komitent
            komitent = Komitent(
                firma_id=firma.id,
                naziv='Komitent d.o.o.',
                pib='87654321',
                maticni_broj='12345678',
                adresa='Adresa 1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='kontakt@komitent.rs',
                broj='1'
            )
            db.session.add(komitent)
            db.session.commit()

            # Create user
            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create faktura
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='F-2025-001',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 15),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 14),
                ukupan_iznos_rsd=Decimal('12000.00'),
                status='izdata'
            )
            db.session.add(faktura)
            db.session.commit()

            # Create KPO entry
            kpo_entry = KPOEntry(
                firma_id=firma.id,
                faktura_id=faktura.id,
                redni_broj=5,
                broj_fakture='F-2025-001',
                datum_prometa=date(2025, 1, 15),
                datum_dospeca=date(2025, 2, 14),
                komitent_naziv='Komitent d.o.o.',
                komitent_pib='87654321',
                opis='Test',
                iznos_rsd=Decimal('12000.00'),
                valuta='RSD',
                status_fakture='izdata',
                godina=2025
            )
            db.session.add(kpo_entry)
            db.session.commit()

            expected = '<KPOEntry 5/2025 - Faktura F-2025-001 - 12000.00 RSD>'
            assert repr(kpo_entry) == expected
