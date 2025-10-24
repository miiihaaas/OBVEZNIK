"""Unit tests for Komitent forms."""
import pytest
from flask_login import login_user
from app import db
from app.models.komitent import Komitent
from app.models.pausaln_firma import PausalnFirma
from app.models.user import User
from app.forms.komitent import KomitentCreateForm, KomitentEditForm


class TestKomitentCreateForm:
    """Tests for KomitentCreateForm validation."""

    def test_form_valid_data(self, app):
        """Test form validation with all valid data."""
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
                email='test@firma.rs',
                dinarski_racuni=[{'banka': 'test', 'broj': '123'}]
            )
            db.session.add(firma)
            db.session.commit()

            # Create pausalac user
            pausalac = User(
                email='pausalac@test.com',
                full_name='Pausalac Test',
                role='pausalac',
                firma_id=firma.id
            )
            pausalac.set_password('password123')
            db.session.add(pausalac)
            db.session.commit()

            pausalac_id = pausalac.id

        with app.test_request_context():
            pausalac = db.session.get(User, pausalac_id)
            login_user(pausalac)

            form = KomitentCreateForm(
                pib='98765432',
                naziv='Test Komitent DOO',
                maticni_broj='87654321',
                adresa='Kneza Miloša',
                broj='10',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='komitent@test.rs'
            )

            assert form.validate() is True

    def test_pib_format_validation(self, app):
        """Test PIB format validation (must be 8 or 9 digits)."""
        with app.app_context():
            # Create test firma and user
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
                email='test@firma.rs',
                dinarski_racuni=[{'banka': 'test', 'broj': '123'}]
            )
            db.session.add(firma)
            db.session.commit()

            pausalac = User(
                email='pausalac@test.com',
                full_name='Pausalac Test',
                role='pausalac',
                firma_id=firma.id
            )
            pausalac.set_password('password123')
            db.session.add(pausalac)
            db.session.commit()
            pausalac_id = pausalac.id

        with app.test_request_context():
            pausalac = db.session.get(User, pausalac_id)
            login_user(pausalac)

            # Test short PIB (should fail)
            form = KomitentCreateForm(
                pib='1234567',  # 7 digits
                naziv='Test Komitent',
                maticni_broj='12345678',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='test@test.rs'
            )
            assert form.validate() is False
            assert 'pib' in form.errors

            # Test 8 digits (should pass)
            form = KomitentCreateForm(
                pib='12345678',
                naziv='Test',
                maticni_broj='87654321',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='test@test.rs'
            )
            assert form.validate() is True

            # Test 9 digits (should pass)
            form = KomitentCreateForm(
                pib='123456789',
                naziv='Test',
                maticni_broj='98765432',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='test@test.rs'
            )
            assert form.validate() is True

    def test_pib_uniqueness_validation_within_firma(self, app):
        """Test that duplicate PIB within same firma is rejected."""
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
                email='test@firma.rs',
                dinarski_racuni=[{'banka': 'test', 'broj': '123'}]
            )
            db.session.add(firma)
            db.session.commit()

            # Create pausalac user
            pausalac = User(
                email='pausalac@test.com',
                full_name='Pausalac Test',
                role='pausalac',
                firma_id=firma.id
            )
            pausalac.set_password('password123')
            db.session.add(pausalac)
            db.session.commit()

            # Create existing komitent
            komitent = Komitent(
                firma_id=firma.id,
                pib='98765432',
                maticni_broj='87654321',
                naziv='Existing Komitent',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='existing@test.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            pausalac_id = pausalac.id

        with app.test_request_context():
            pausalac = db.session.get(User, pausalac_id)
            login_user(pausalac)

            # Try to create form with same PIB in same firma
            form = KomitentCreateForm(
                pib='98765432',  # Duplicate
                naziv='New Komitent',
                maticni_broj='11111111',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='new@test.rs'
            )

            assert form.validate() is False
            assert 'pib' in form.errors

    def test_email_format_validation(self, app):
        """Test email format validation."""
        with app.app_context():
            # Create test data
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
                email='test@firma.rs',
                dinarski_racuni=[{'banka': 'test', 'broj': '123'}]
            )
            db.session.add(firma)
            db.session.commit()

            pausalac = User(
                email='pausalac@test.com',
                full_name='Pausalac Test',
                role='pausalac',
                firma_id=firma.id
            )
            pausalac.set_password('password123')
            db.session.add(pausalac)
            db.session.commit()
            pausalac_id = pausalac.id

        with app.test_request_context():
            pausalac = db.session.get(User, pausalac_id)
            login_user(pausalac)

            # Test invalid email format
            form = KomitentCreateForm(
                pib='12345678',
                naziv='Test',
                maticni_broj='87654321',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='invalid-email'
            )
            assert form.validate() is False
            assert 'email' in form.errors

            # Test valid email format
            form = KomitentCreateForm(
                pib='12345678',
                naziv='Test',
                maticni_broj='87654321',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='valid@test.rs'
            )
            assert form.validate() is True

    def test_missing_required_fields(self, app):
        """Test that missing required fields fail validation."""
        with app.test_request_context():
            # Missing PIB
            form = KomitentCreateForm(
                naziv='Test',
                maticni_broj='87654321',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='test@test.rs'
            )
            assert form.validate() is False
            assert 'pib' in form.errors


class TestKomitentEditForm:
    """Tests for KomitentEditForm validation."""

    def test_form_valid_data(self, app):
        """Test edit form validation with valid data."""
        with app.test_request_context():
            form = KomitentEditForm(
                pib='98765432',
                naziv='Updated Komitent',
                maticni_broj='87654321',
                adresa='Updated Street',
                broj='20',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='updated@test.rs'
            )

            assert form.validate() is True

    def test_pib_readonly(self, app):
        """Test that PIB field exists and has readonly attribute in render_kw."""
        with app.test_request_context():
            form = KomitentEditForm()
            assert hasattr(form, 'pib')
            assert 'readonly' in form.pib.render_kw

    def test_email_format_validation_edit(self, app):
        """Test email format validation in edit form."""
        with app.test_request_context():
            # Invalid email
            form = KomitentEditForm(
                pib='12345678',
                naziv='Test',
                maticni_broj='87654321',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='invalid-email'
            )
            assert form.validate() is False
            assert 'email' in form.errors

            # Valid email
            form = KomitentEditForm(
                pib='12345678',
                naziv='Test',
                maticni_broj='87654321',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='valid@test.rs'
            )
            assert form.validate() is True
