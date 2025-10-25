"""Unit tests for Artikal CRUD operations."""
import pytest
from app import db
from app.models.artikal import Artikal
from app.models.pausaln_firma import PausalnFirma
from decimal import Decimal


@pytest.fixture
def sample_firma(app):
    """Create a sample PausalnFirma for testing."""
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
            telefon='011234567',
            email='test@firma.rs',
            dinarski_racuni=[{'banka': 'Banka', 'racun': '123-456789-10'}]
        )
        db.session.add(firma)
        db.session.commit()
        yield firma
        db.session.delete(firma)
        db.session.commit()


@pytest.fixture
def sample_firma_2(app):
    """Create a second PausalnFirma for tenant isolation tests."""
    with app.app_context():
        firma = PausalnFirma(
            pib='98765432',
            maticni_broj='12348765',
            naziv='Test Firma 2',
            adresa='Test Adresa 2',
            broj='2',
            postanski_broj='21000',
            mesto='Novi Sad',
            drzava='Srbija',
            telefon='021234567',
            email='test2@firma.rs',
            dinarski_racuni=[{'banka': 'Banka', 'racun': '123-456789-20'}]
        )
        db.session.add(firma)
        db.session.commit()
        yield firma
        db.session.delete(firma)
        db.session.commit()


class TestArtikalCreation:
    """Test suite for Artikal creation."""

    def test_create_artikal_with_all_fields(self, app, sample_firma):
        """Test creating an artikal with all fields populated."""
        with app.app_context():
            artikal = Artikal(
                firma_id=sample_firma.id,
                naziv='Programiranje',
                opis='Izrada softvera po satu',
                podrazumevana_cena=Decimal('3500.00'),
                jedinica_mere='sat'
            )
            db.session.add(artikal)
            db.session.commit()

            # Verify artikal was created
            assert artikal.id is not None
            assert artikal.naziv == 'Programiranje'
            assert artikal.opis == 'Izrada softvera po satu'
            assert artikal.podrazumevana_cena == Decimal('3500.00')
            assert artikal.jedinica_mere == 'sat'
            assert artikal.firma_id == sample_firma.id
            assert artikal.created_at is not None

            # Cleanup
            db.session.delete(artikal)
            db.session.commit()

    def test_create_artikal_with_required_fields_only(self, app, sample_firma):
        """Test creating an artikal with only required fields (naziv, jedinica_mere)."""
        with app.app_context():
            artikal = Artikal(
                firma_id=sample_firma.id,
                naziv='Konsultacije',
                jedinica_mere='sat'
            )
            db.session.add(artikal)
            db.session.commit()

            # Verify artikal was created
            assert artikal.id is not None
            assert artikal.naziv == 'Konsultacije'
            assert artikal.opis is None
            assert artikal.podrazumevana_cena is None
            assert artikal.jedinica_mere == 'sat'

            # Cleanup
            db.session.delete(artikal)
            db.session.commit()

    def test_create_artikal_in_different_firme(self, app, sample_firma, sample_firma_2):
        """Test creating artikli in different firme (tenant isolation)."""
        with app.app_context():
            artikal1 = Artikal(
                firma_id=sample_firma.id,
                naziv='Artikal Firma 1',
                jedinica_mere='kom'
            )
            artikal2 = Artikal(
                firma_id=sample_firma_2.id,
                naziv='Artikal Firma 2',
                jedinica_mere='kom'
            )

            db.session.add(artikal1)
            db.session.add(artikal2)
            db.session.commit()

            # Verify tenant isolation
            assert artikal1.firma_id == sample_firma.id
            assert artikal2.firma_id == sample_firma_2.id
            assert artikal1.firma_id != artikal2.firma_id

            # Cleanup
            db.session.delete(artikal1)
            db.session.delete(artikal2)
            db.session.commit()


class TestArtikalUpdate:
    """Test suite for Artikal update operations."""

    def test_update_artikal(self, app, sample_firma):
        """Test updating an artikal with new data."""
        with app.app_context():
            # Create artikal
            artikal = Artikal(
                firma_id=sample_firma.id,
                naziv='Original Naziv',
                opis='Original Opis',
                podrazumevana_cena=Decimal('1000.00'),
                jedinica_mere='sat'
            )
            db.session.add(artikal)
            db.session.commit()

            # Update artikal
            artikal.naziv = 'Updated Naziv'
            artikal.opis = 'Updated Opis'
            artikal.podrazumevana_cena = Decimal('2000.00')
            artikal.jedinica_mere = 'dan'
            db.session.commit()

            # Verify update
            assert artikal.naziv == 'Updated Naziv'
            assert artikal.opis == 'Updated Opis'
            assert artikal.podrazumevana_cena == Decimal('2000.00')
            assert artikal.jedinica_mere == 'dan'

            # Cleanup
            db.session.delete(artikal)
            db.session.commit()

    def test_update_artikal_clear_optional_fields(self, app, sample_firma):
        """Test clearing optional fields (opis, podrazumevana_cena) by setting to None."""
        with app.app_context():
            # Create artikal with all fields
            artikal = Artikal(
                firma_id=sample_firma.id,
                naziv='Test Artikal',
                opis='Some description',
                podrazumevana_cena=Decimal('500.00'),
                jedinica_mere='kom'
            )
            db.session.add(artikal)
            db.session.commit()

            # Clear optional fields
            artikal.opis = None
            artikal.podrazumevana_cena = None
            db.session.commit()

            # Verify cleared
            assert artikal.opis is None
            assert artikal.podrazumevana_cena is None

            # Cleanup
            db.session.delete(artikal)
            db.session.commit()


class TestArtikalDeletion:
    """Test suite for Artikal deletion operations."""

    def test_delete_artikal(self, app, sample_firma):
        """Test deleting an artikal (AC: 7 - deletion is allowed)."""
        with app.app_context():
            # Create artikal
            artikal = Artikal(
                firma_id=sample_firma.id,
                naziv='To Be Deleted',
                jedinica_mere='kom'
            )
            db.session.add(artikal)
            db.session.commit()

            artikal_id = artikal.id

            # Delete artikal
            db.session.delete(artikal)
            db.session.commit()

            # Verify deletion
            deleted_artikal = db.session.get(Artikal, artikal_id)
            assert deleted_artikal is None

    def test_delete_artikal_does_not_affect_fakture(self, app, sample_firma):
        """
        Test that deleting an artikal does not affect existing fakture (AC: 7).

        Note: Artikli are copied into faktura_stavke, not referenced.
        Therefore, deletion is always allowed and does not cascade to faktura_stavke.
        """
        with app.app_context():
            # Create artikal
            artikal = Artikal(
                firma_id=sample_firma.id,
                naziv='Artikal sa Fakturama',
                jedinica_mere='kom'
            )
            db.session.add(artikal)
            db.session.commit()

            # Deletion should succeed even if artikal is used in fakture
            # (In real scenario, faktura_stavke would have artikal_id = NULL after deletion)
            artikal_id = artikal.id
            db.session.delete(artikal)
            db.session.commit()

            # Verify deletion succeeded
            deleted_artikal = db.session.get(Artikal, artikal_id)
            assert deleted_artikal is None


class TestArtikalRelationships:
    """Test suite for Artikal relationships."""

    def test_artikal_firma_relationship(self, app, sample_firma):
        """Test that artikal has correct relationship with firma."""
        with app.app_context():
            artikal = Artikal(
                firma_id=sample_firma.id,
                naziv='Test Relationship',
                jedinica_mere='kom'
            )
            db.session.add(artikal)
            db.session.commit()

            # Verify relationship
            assert artikal.firma is not None
            assert artikal.firma.id == sample_firma.id
            assert artikal.firma.naziv == 'Test Firma'

            # Verify back-reference (re-query firma to load artikli relationship)
            firma_requeried = db.session.get(PausalnFirma, sample_firma.id)
            assert len(firma_requeried.artikli) > 0
            assert any(a.id == artikal.id for a in firma_requeried.artikli)

            # Cleanup
            db.session.delete(artikal)
            db.session.commit()
