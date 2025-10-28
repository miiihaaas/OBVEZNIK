"""Unit tests for Faktura forms."""
import pytest
from datetime import date
from decimal import Decimal
from app import db
from app.forms.faktura import FakturaCreateForm, FakturaStavkaForm
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.komitent import Komitent
from flask_login import login_user


@pytest.fixture
def pausalac_user(app):
    """Create a test pausalac user with firma."""
    firma = PausalnFirma(
        pib='123456789',
        maticni_broj='12345678',
        naziv='Test Firma',
        adresa='Test Adresa',
        broj='1',
        postanski_broj='11000',
        mesto='Beograd',
        telefon='011111111',
        email='firma@test.com',
        dinarski_racuni=[{'banka': 'Test Banka', 'broj': '123-456789-00'}]
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
    return user


class TestFakturaStavkaForm:
    """Tests for FakturaStavkaForm."""

    def test_stavka_form_valid_data(self, app):
        """Test that FakturaStavkaForm accepts valid data."""
        with app.test_request_context():
            form = FakturaStavkaForm(
                naziv='Konsultantske usluge',
                kolicina=Decimal('10.00'),
                jedinica_mere='h',
                cena=Decimal('5000.00'),
                ukupno=Decimal('50000.00'),
                redni_broj=1
            )
            assert form.validate()

    def test_stavka_form_validates_kolicina_positive(self, app):
        """Test that FakturaStavkaForm validation fails if kolicina <= 0."""
        with app.test_request_context():
            form = FakturaStavkaForm(
                naziv='Test usluga',
                kolicina=Decimal('0.00'),
                jedinica_mere='h',
                cena=Decimal('1000.00')
            )
            assert not form.validate()
            assert 'kolicina' in form.errors

    def test_stavka_form_validates_cena_positive(self, app):
        """Test that FakturaStavkaForm validation fails if cena <= 0."""
        with app.test_request_context():
            form = FakturaStavkaForm(
                naziv='Test usluga',
                kolicina=Decimal('1.00'),
                jedinica_mere='h',
                cena=Decimal('0.00')
            )
            assert not form.validate()
            assert 'cena' in form.errors

    def test_stavka_form_requires_naziv(self, app):
        """Test that FakturaStavkaForm requires naziv."""
        with app.test_request_context():
            form = FakturaStavkaForm(
                kolicina=Decimal('1.00'),
                jedinica_mere='h',
                cena=Decimal('1000.00')
            )
            assert not form.validate()
            assert 'naziv' in form.errors


class TestFakturaCreateForm:
    """Tests for FakturaCreateForm."""

    def test_form_default_values(self, app):
        """Test that FakturaCreateForm has correct default values."""
        with app.test_request_context():
            form = FakturaCreateForm()
            assert form.tip_fakture.data == 'standardna'
            assert form.datum_prometa.data == date.today()
            assert form.valuta_placanja.data == 7

    def test_form_validates_without_komitent(self, app):
        """Test that validation fails if komitent is not selected."""
        with app.test_request_context():
            form = FakturaCreateForm(
                tip_fakture='standardna',
                datum_prometa=date.today(),
                valuta_placanja=7,
                stavke=[
                    {
                        'naziv': 'Test usluga',
                        'kolicina': Decimal('1.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('1000.00')
                    }
                ]
            )
            assert not form.validate()
            assert 'komitent_id' in form.errors

    def test_form_validates_poziv_na_broj_format(self, app, pausalac_user):
        """Test that poziv_na_broj must start with 95 or 97."""
        with app.test_request_context():
            # Login user to set firma context
            login_user(pausalac_user)

            # Create komitent for this firma
            komitent = Komitent(
                firma_id=pausalac_user.firma_id,
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Komitent',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='test@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            # Test with invalid poziv_na_broj (doesn't start with 95 or 97)
            form = FakturaCreateForm(
                tip_fakture='standardna',
                komitent_id=komitent.id,
                datum_prometa=date.today(),
                valuta_placanja=7,
                poziv_na_broj='1234567890',  # Invalid - doesn't start with 95 or 97
                stavke=[
                    {
                        'naziv': 'Test usluga',
                        'kolicina': Decimal('1.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('1000.00')
                    }
                ]
            )
            assert not form.validate()
            assert 'poziv_na_broj' in form.errors

    def test_form_accepts_valid_poziv_na_broj_95(self, app, pausalac_user):
        """Test that poziv_na_broj starting with 95 is accepted."""
        with app.test_request_context():
            # Login user to set firma context
            login_user(pausalac_user)

            # Create komitent for this firma
            komitent = Komitent(
                firma_id=pausalac_user.firma_id,
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Komitent',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='test@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            # Test with valid poziv_na_broj starting with 95
            form = FakturaCreateForm(
                tip_fakture='standardna',
                komitent_id=komitent.id,
                datum_prometa=date.today(),
                valuta_placanja=7,
                poziv_na_broj='951234567890',
                stavke=[
                    {
                        'naziv': 'Test usluga',
                        'kolicina': Decimal('1.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('1000.00')
                    }
                ]
            )
            assert form.validate()

    def test_form_accepts_valid_poziv_na_broj_97(self, app, pausalac_user):
        """Test that poziv_na_broj starting with 97 is accepted."""
        with app.test_request_context():
            # Login user to set firma context
            login_user(pausalac_user)

            # Create komitent for this firma
            komitent = Komitent(
                firma_id=pausalac_user.firma_id,
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Komitent',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='test@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            # Test with valid poziv_na_broj starting with 97
            form = FakturaCreateForm(
                tip_fakture='standardna',
                komitent_id=komitent.id,
                datum_prometa=date.today(),
                valuta_placanja=7,
                poziv_na_broj='971234567890',
                stavke=[
                    {
                        'naziv': 'Test usluga',
                        'kolicina': Decimal('1.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('1000.00')
                    }
                ]
            )
            assert form.validate()

    def test_form_validates_without_stavke(self, app, pausalac_user):
        """Test that validation fails if no stavke are provided."""
        with app.test_request_context():
            # Login user to set firma context
            login_user(pausalac_user)

            # Create komitent for this firma
            komitent = Komitent(
                firma_id=pausalac_user.firma_id,
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Komitent',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='test@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            # Test without stavke
            form = FakturaCreateForm(
                tip_fakture='standardna',
                komitent_id=komitent.id,
                datum_prometa=date.today(),
                valuta_placanja=7,
                stavke=[]
            )
            assert not form.validate()
            assert 'stavke' in form.errors

    def test_devizna_faktura_requires_valuta(self, app, pausalac_user):
        """Test that devizna faktura requires valuta_fakture."""
        with app.app_context():
            with app.test_request_context():
                login_user(pausalac_user)

                # Create komitent with IBAN and SWIFT
                komitent = Komitent(
                    firma_id=pausalac_user.firma_id,
                    pib='12345678',
                    maticni_broj='87654321',
                    naziv='Foreign Komitent',
                    adresa='Main Street',
                    broj='100',
                    postanski_broj='10000',
                    mesto='Berlin',
                    drzava='Germany',
                    email='test@foreign.com',
                    iban='DE89370400440532013000',
                    swift='COBADEFFXXX'
                )
                db.session.add(komitent)
                db.session.commit()

                # Test devizna faktura without valuta_fakture
                form = FakturaCreateForm(
                    tip_fakture='devizna',
                    komitent_id=komitent.id,
                    datum_prometa=date.today(),
                    valuta_placanja=7,
                    valuta_fakture='',  # Empty valuta
                    srednji_kurs=Decimal('117.5432'),
                    stavke=[{
                        'naziv': 'Consulting',
                        'kolicina': Decimal('10.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('100.00')
                    }]
                )
                assert not form.validate()
                assert 'valuta_fakture' in form.errors

    def test_devizna_faktura_requires_srednji_kurs(self, app, pausalac_user):
        """Test that devizna faktura requires srednji_kurs."""
        with app.app_context():
            with app.test_request_context():
                login_user(pausalac_user)

                komitent = Komitent(
                    firma_id=pausalac_user.firma_id,
                    pib='12345678',
                    maticni_broj='87654321',
                    naziv='Foreign Komitent',
                    adresa='Main Street',
                    broj='100',
                    postanski_broj='10000',
                    mesto='Berlin',
                    drzava='Germany',
                    email='test@foreign.com',
                    iban='DE89370400440532013000',
                    swift='COBADEFFXXX'
                )
                db.session.add(komitent)
                db.session.commit()

                # Test devizna faktura without srednji_kurs
                form = FakturaCreateForm(
                    tip_fakture='devizna',
                    komitent_id=komitent.id,
                    datum_prometa=date.today(),
                    valuta_placanja=7,
                    valuta_fakture='EUR',
                    srednji_kurs=None,  # No kurs
                    stavke=[{
                        'naziv': 'Consulting',
                        'kolicina': Decimal('10.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('100.00')
                    }]
                )
                assert not form.validate()
                assert 'srednji_kurs' in form.errors

    def test_devizna_faktura_requires_komitent_iban_swift(self, app, pausalac_user):
        """Test that devizna faktura requires komitent with IBAN and SWIFT."""
        with app.app_context():
            with app.test_request_context():
                login_user(pausalac_user)

                # Create komitent WITHOUT IBAN and SWIFT
                komitent = Komitent(
                    firma_id=pausalac_user.firma_id,
                    pib='12345678',
                    maticni_broj='87654321',
                    naziv='Domestic Komitent',
                    adresa='Test',
                    broj='1',
                    postanski_broj='11000',
                    mesto='Beograd',
                    drzava='Srbija',
                    email='test@domestic.rs'
                    # No IBAN, no SWIFT
                )
                db.session.add(komitent)
                db.session.commit()

                # Test devizna faktura with komitent without IBAN/SWIFT
                form = FakturaCreateForm(
                    tip_fakture='devizna',
                    komitent_id=komitent.id,
                    datum_prometa=date.today(),
                    valuta_placanja=7,
                    valuta_fakture='EUR',
                    srednji_kurs=Decimal('117.5432'),
                    stavke=[{
                        'naziv': 'Consulting',
                        'kolicina': Decimal('10.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('100.00')
                    }]
                )
                assert not form.validate()
                assert 'komitent_id' in form.errors

    def test_standardna_faktura_cannot_have_valuta(self, app, pausalac_user):
        """Test that standardna faktura cannot have valuta_fakture."""
        with app.app_context():
            with app.test_request_context():
                login_user(pausalac_user)

                komitent = Komitent(
                    firma_id=pausalac_user.firma_id,
                    pib='12345678',
                    maticni_broj='87654321',
                    naziv='Test Komitent',
                    adresa='Test',
                    broj='1',
                    postanski_broj='11000',
                    mesto='Beograd',
                    drzava='Srbija',
                    email='test@test.rs'
                )
                db.session.add(komitent)
                db.session.commit()

                # Test standardna faktura WITH valuta_fakture (should fail)
                form = FakturaCreateForm(
                    tip_fakture='standardna',
                    komitent_id=komitent.id,
                    datum_prometa=date.today(),
                    valuta_placanja=7,
                    valuta_fakture='EUR',  # Should not be allowed
                    srednji_kurs=Decimal('117.5432'),  # Should not be allowed
                    stavke=[{
                        'naziv': 'Usluga',
                        'kolicina': Decimal('10.00'),
                        'jedinica_mere': 'h',
                        'cena': Decimal('5000.00')
                    }]
                )
                assert not form.validate()
                assert 'valuta_fakture' in form.errors or 'srednji_kurs' in form.errors
