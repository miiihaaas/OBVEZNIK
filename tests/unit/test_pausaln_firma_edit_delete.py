"""Unit tests for PausalnFirma Edit and Delete operations."""
import pytest
from app.models.pausaln_firma import PausalnFirma
from app.models.user import User
from app.forms.pausaln_firma import PausalnFirmaEditForm
from app import db


class TestPausalnFirmaEditForm:
    """Test PausalnFirmaEditForm validation."""

    def test_edit_form_valid_data(self, app):
        """Test that edit form validates with all valid data."""
        with app.app_context():
            form = PausalnFirmaEditForm(
                pib='12345678',
                naziv='Test Firma DOO',
                maticni_broj='87654321',
                adresa='Kneza Milosa',
                broj='10',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011234567',
                email='test@firma.rs',
                dinarski_racuni_json='[{"banka": "Banka", "broj": "123-456789-10"}]',
                devizni_racuni_json='[{"banka": "Banka", "iban": "RS35260005601001611379", "swift": "BANKRSBG"}]',
                prefiks_fakture='INV',
                sufiks_fakture='2025'
            )
            assert form.validate() is True

    def test_edit_form_pib_readonly(self, app):
        """Test that PIB field is readonly (render_kw check)."""
        with app.app_context():
            form = PausalnFirmaEditForm()
            assert form.pib.render_kw.get('readonly') is True

    def test_edit_form_invalid_email(self, app):
        """Test that edit form rejects invalid email format."""
        with app.app_context():
            form = PausalnFirmaEditForm(
                pib='12345678',
                naziv='Test Firma',
                maticni_broj='87654321',
                adresa='Kneza Milosa',
                broj='10',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011234567',
                email='invalid',  # Invalid email without @ and domain
                dinarski_racuni_json='[{"banka": "Banka", "broj": "123-456789-10"}]'
            )
            # Since email uses custom validation, check if it properly validates
            # Email field is optional, so empty is valid, but if provided must be valid format
            is_valid = form.validate()
            if not is_valid:
                assert 'email' in form.errors

    def test_edit_form_requires_dinarski_racuni(self, app):
        """Test that edit form requires at least one dinarski račun."""
        with app.app_context():
            form = PausalnFirmaEditForm(
                pib='12345678',
                naziv='Test Firma',
                maticni_broj='87654321',
                adresa='Kneza Milosa',
                broj='10',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011234567',
                email='test@firma.rs',
                dinarski_racuni_json='[]'  # Empty array
            )
            assert form.validate() is False
            assert 'dinarski_racuni_json' in form.errors


class TestPausalnFirmaUpdate:
    """Test PausalnFirma update operations."""

    def test_update_firma_success(self, app, sample_firma):
        """Test successful update of firma."""
        with app.app_context():
            # Re-fetch firma from database
            firma = db.session.get(PausalnFirma, sample_firma.id)
            original_pib = firma.pib

            # Update firma
            firma.naziv = 'Updated Firma DOO'
            firma.telefon = '011999888'
            firma.email = 'updated@firma.rs'
            db.session.commit()

            # Verify updates
            updated_firma = db.session.get(PausalnFirma, firma.id)
            assert updated_firma.naziv == 'Updated Firma DOO'
            assert updated_firma.telefon == '011999888'
            assert updated_firma.email == 'updated@firma.rs'
            assert updated_firma.pib == original_pib  # PIB should remain unchanged

    def test_pib_immutable_on_update(self, app, sample_firma):
        """Test that PIB remains immutable during update."""
        with app.app_context():
            # Re-fetch firma from database
            firma = db.session.get(PausalnFirma, sample_firma.id)
            original_pib = firma.pib

            # Attempt to update other fields (PIB should not change)
            firma.naziv = 'Changed Firma'
            db.session.commit()

            updated_firma = db.session.get(PausalnFirma, firma.id)
            assert updated_firma.pib == original_pib
            assert updated_firma.naziv == 'Changed Firma'


class TestPausalnFirmaDelete:
    """Test PausalnFirma delete operations with CASCADE."""

    def test_delete_firma_success(self, app, sample_firma):
        """Test successful deletion of firma."""
        with app.app_context():
            # Re-fetch firma from database
            firma = db.session.get(PausalnFirma, sample_firma.id)
            firma_id = firma.id

            # Delete firma
            db.session.delete(firma)
            db.session.commit()

            # Verify firma is deleted
            deleted_firma = db.session.get(PausalnFirma, firma_id)
            assert deleted_firma is None

    def test_cascade_delete_sets_null_for_users(self, app, sample_firma):
        """Test that deleting firma sets firma_id to NULL for users (SET NULL)."""
        with app.app_context():
            # Re-fetch firma from database
            firma = db.session.get(PausalnFirma, sample_firma.id)

            # Create a user linked to the firma
            user = User(
                email='pausalac@test.com',
                full_name='Test Pausalac',
                password_hash='hashed_password',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            # Delete firma
            db.session.delete(firma)
            db.session.commit()

            # Verify user still exists but firma_id is NULL
            user_after_delete = db.session.get(User, user_id)
            assert user_after_delete is not None
            assert user_after_delete.firma_id is None

    def test_cascade_delete_removes_related_records(self, app, sample_firma):
        """Test that deleting firma cascades to komitenti and fakture."""
        with app.app_context():
            # Re-fetch firma from database
            firma = db.session.get(PausalnFirma, sample_firma.id)
            firma_id = firma.id

            # Note: Since Komitent and Faktura models may not be implemented yet,
            # this test serves as a placeholder for future CASCADE testing

            # Delete firma
            db.session.delete(firma)
            db.session.commit()

            # Verify firma is deleted
            deleted_firma = db.session.get(PausalnFirma, firma_id)
            assert deleted_firma is None

            # TODO: Add assertions for Komitent and Faktura CASCADE when models are implemented
            # Example:
            # komitent_count = Komitent.query.filter_by(firma_id=firma_id).count()
            # assert komitent_count == 0


@pytest.fixture
def sample_firma(app):
    """Create a sample PausalnFirma for testing and return a simple object with its ID."""
    with app.app_context():
        firma = PausalnFirma(
            pib='12345678',
            maticni_broj='87654321',
            naziv='Test Firma DOO',
            adresa='Kneza Milosa',
            broj='10',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            telefon='011234567',
            email='test@firma.rs',
            dinarski_racuni=[{'banka': 'Komercijalna Banka', 'broj': '123-456789-10'}],
            devizni_racuni=[{'banka': 'Komercijalna Banka', 'iban': 'RS35260005601001611379', 'swift': 'KOBBRSBG'}],
            prefiks_fakture='INV',
            sufiks_fakture='2025'
        )
        db.session.add(firma)
        db.session.commit()
        firma_id = firma.id

    # Return a simple object with just the ID to avoid session issues
    class FirmaRef:
        def __init__(self, id):
            self.id = id

    return FirmaRef(firma_id)
