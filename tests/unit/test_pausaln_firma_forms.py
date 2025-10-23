"""Unit tests for PausalnFirma forms."""
import pytest
import json
from app import db
from app.models.pausaln_firma import PausalnFirma
from app.forms.pausaln_firma import PausalnFirmaCreateForm


class TestPausalnFirmaCreateForm:
    """Tests for PausalnFirmaCreateForm validation."""

    def test_form_valid_data(self, app):
        """Test form validation with all valid data."""
        with app.app_context():
            form = PausalnFirmaCreateForm(
                pib='12345678',
                naziv='Test Firma DOO',
                maticni_broj='87654321',
                adresa='Kneza Miloša',
                broj='12',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='+381 11 1234567',
                email='info@testfirma.rs',
                dinarski_racuni_json=json.dumps([{'banka': 'Intesa', 'broj': '160-123456-78'}]),
                prefiks_fakture='TEST',
                sufiks_fakture='/2025',
                pdv_kategorija='SS',
                sifra_osnova='PDV-RS-33'
            )

            assert form.validate() is True

    def test_pib_format_validation(self, app):
        """Test PIB format validation (must be exactly 8 digits)."""
        with app.app_context():
            # Test short PIB
            form = PausalnFirmaCreateForm(
                pib='1234567',  # 7 digits
                naziv='Test',
                maticni_broj='12345678',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                dinarski_racuni_json=json.dumps([{'banka': 'test', 'broj': '123'}])
            )
            assert form.validate() is False
            assert 'pib' in form.errors

            # Test long PIB
            form = PausalnFirmaCreateForm(
                pib='123456789',  # 9 digits
                naziv='Test',
                maticni_broj='12345678',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                dinarski_racuni_json=json.dumps([{'banka': 'test', 'broj': '123'}])
            )
            assert form.validate() is False
            assert 'pib' in form.errors

            # Test non-numeric PIB
            form = PausalnFirmaCreateForm(
                pib='1234567a',
                naziv='Test',
                maticni_broj='12345678',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                dinarski_racuni_json=json.dumps([{'banka': 'test', 'broj': '123'}])
            )
            assert form.validate() is False
            assert 'pib' in form.errors

    def test_pib_uniqueness_validation(self, app):
        """Test that duplicate PIB is rejected."""
        with app.app_context():
            # Create existing firma
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Existing Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[{'banka': 'test', 'broj': '123'}]
            )
            db.session.add(firma)
            db.session.commit()

            # Try to create form with same PIB
            form = PausalnFirmaCreateForm(
                pib='12345678',  # Duplicate
                naziv='New Firma',
                maticni_broj='11111111',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                dinarski_racuni_json=json.dumps([{'banka': 'test', 'broj': '123'}])
            )

            assert form.validate() is False
            assert 'pib' in form.errors
            assert 'već postoji' in form.errors['pib'][0]

    def test_missing_required_fields(self, app):
        """Test that missing required fields are caught."""
        with app.app_context():
            # Missing naziv
            form = PausalnFirmaCreateForm(
                pib='12345678',
                maticni_broj='87654321',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                dinarski_racuni_json=json.dumps([{'banka': 'test', 'broj': '123'}])
            )
            assert form.validate() is False
            assert 'naziv' in form.errors

    def test_email_format_validation(self, app):
        """Test email format validation."""
        with app.app_context():
            # Invalid email format
            form = PausalnFirmaCreateForm(
                pib='12345678',
                naziv='Test Firma',
                maticni_broj='87654321',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='invalid-email',  # Invalid
                dinarski_racuni_json=json.dumps([{'banka': 'test', 'broj': '123'}])
            )
            assert form.validate() is False
            assert 'email' in form.errors

            # Valid email
            form = PausalnFirmaCreateForm(
                pib='12345678',
                naziv='Test Firma',
                maticni_broj='87654321',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='valid@email.com',
                dinarski_racuni_json=json.dumps([{'banka': 'test', 'broj': '123'}])
            )
            assert form.validate() is True

    def test_dinarski_racuni_required(self, app):
        """Test that at least one dinarski račun is required."""
        with app.app_context():
            # Empty dinarski računi
            form = PausalnFirmaCreateForm(
                pib='12345678',
                naziv='Test Firma',
                maticni_broj='87654321',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                dinarski_racuni_json=''  # Empty
            )
            assert form.validate() is False
            assert 'dinarski_racuni_json' in form.errors

            # Empty array
            form = PausalnFirmaCreateForm(
                pib='12345678',
                naziv='Test Firma',
                maticni_broj='87654321',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                dinarski_racuni_json=json.dumps([])
            )
            assert form.validate() is False
            assert 'dinarski_racuni_json' in form.errors

    def test_maticni_broj_length(self, app):
        """Test matični broj must be exactly 8 characters."""
        with app.app_context():
            # Short matični broj
            form = PausalnFirmaCreateForm(
                pib='12345678',
                naziv='Test Firma',
                maticni_broj='1234567',  # 7 chars
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                dinarski_racuni_json=json.dumps([{'banka': 'test', 'broj': '123'}])
            )
            assert form.validate() is False
            assert 'maticni_broj' in form.errors

    def test_optional_fields(self, app):
        """Test that optional fields are truly optional."""
        with app.app_context():
            form = PausalnFirmaCreateForm(
                pib='12345678',
                naziv='Test Firma',
                maticni_broj='87654321',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                # email - optional, not provided
                # devizni_racuni_json - optional, not provided
                # prefiks_fakture - optional, not provided
                # sufiks_fakture - optional, not provided
                dinarski_racuni_json=json.dumps([{'banka': 'test', 'broj': '123'}])
            )
            assert form.validate() is True

    def test_prefiks_suffix_length_validation(self, app):
        """Test that prefiks and sufiks have max length of 10 chars."""
        with app.app_context():
            # Prefiks too long
            form = PausalnFirmaCreateForm(
                pib='12345678',
                naziv='Test Firma',
                maticni_broj='87654321',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                prefiks_fakture='12345678901',  # 11 chars
                dinarski_racuni_json=json.dumps([{'banka': 'test', 'broj': '123'}])
            )
            assert form.validate() is False
            assert 'prefiks_fakture' in form.errors
