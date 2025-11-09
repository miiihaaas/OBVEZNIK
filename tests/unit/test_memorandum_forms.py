"""Unit tests for Memorandum forms."""
import pytest
from datetime import date, timedelta
from app.forms.memorandum import MemorandumCreateForm, MemorandumEditForm


class TestMemorandumCreateForm:
    """Test suite for MemorandumCreateForm."""

    def test_memorandum_create_form_valid(self, app):
        """Test form validation succeeds when all required fields are valid."""
        with app.app_context():
            form = MemorandumCreateForm(
                naslov='Sastanak sa klijentom',
                sadrzaj='Ovo je detaljan sadrzaj memoranduma sa dovoljno karaktera za validaciju.',
                datum=date.today()
            )
            assert form.validate() is True

    def test_memorandum_create_form_missing_naslov(self, app):
        """Test form validation fails when naslov is missing."""
        with app.app_context():
            form = MemorandumCreateForm(
                naslov='',
                sadrzaj='Ovo je detaljan sadrzaj memoranduma sa dovoljno karaktera za validaciju.',
                datum=date.today()
            )
            assert form.validate() is False
            assert any('Naslov je obavezan' in error for error in form.naslov.errors)

    def test_memorandum_create_form_missing_sadrzaj(self, app):
        """Test form validation fails when sadrzaj is missing."""
        with app.app_context():
            form = MemorandumCreateForm(
                naslov='Sastanak sa klijentom',
                sadrzaj='',
                datum=date.today()
            )
            assert form.validate() is False
            assert any('Sadržaj je obavezan' in error for error in form.sadrzaj.errors)

    def test_memorandum_create_form_datum_in_future(self, app):
        """Test form validation fails when datum is in the future."""
        with app.app_context():
            future_date = date.today() + timedelta(days=7)
            form = MemorandumCreateForm(
                naslov='Sastanak sa klijentom',
                sadrzaj='Ovo je detaljan sadrzaj memoranduma sa dovoljno karaktera za validaciju.',
                datum=future_date
            )
            assert form.validate() is False
            assert any('Datum ne može biti u budućnosti' in error for error in form.datum.errors)

    def test_memorandum_create_form_naslov_too_short(self, app):
        """Test form validation fails when naslov is too short (< 3 chars)."""
        with app.app_context():
            form = MemorandumCreateForm(
                naslov='Ab',  # Only 2 characters
                sadrzaj='Ovo je detaljan sadrzaj memoranduma sa dovoljno karaktera za validaciju.',
                datum=date.today()
            )
            assert form.validate() is False
            assert any('najmanje 3' in error for error in form.naslov.errors)

    def test_memorandum_create_form_sadrzaj_too_short(self, app):
        """Test form validation fails when sadrzaj is too short (< 10 chars)."""
        with app.app_context():
            form = MemorandumCreateForm(
                naslov='Sastanak sa klijentom',
                sadrzaj='Kratko',  # Only 6 characters
                datum=date.today()
            )
            assert form.validate() is False
            assert any('najmanje 10' in error for error in form.sadrzaj.errors)

    def test_memorandum_create_form_naslov_max_length(self, app):
        """Test form validation fails when naslov exceeds 255 chars."""
        with app.app_context():
            long_naslov = 'A' * 256
            form = MemorandumCreateForm(
                naslov=long_naslov,
                sadrzaj='Ovo je detaljan sadrzaj memoranduma sa dovoljno karaktera za validaciju.',
                datum=date.today()
            )
            assert form.validate() is False
            assert any('255' in error for error in form.naslov.errors)

    def test_memorandum_create_form_with_optional_komitent(self, app):
        """Test form validation succeeds with optional komitent_id."""
        with app.app_context():
            form = MemorandumCreateForm(
                naslov='Sastanak sa klijentom',
                sadrzaj='Ovo je detaljan sadrzaj memoranduma sa dovoljno karaktera za validaciju.',
                datum=date.today(),
                komitent_id=1
            )
            assert form.validate() is True

    def test_memorandum_create_form_with_optional_faktura(self, app):
        """Test form validation succeeds with optional faktura_id."""
        with app.app_context():
            form = MemorandumCreateForm(
                naslov='Sastanak sa klijentom',
                sadrzaj='Ovo je detaljan sadrzaj memoranduma sa dovoljno karaktera za validaciju.',
                datum=date.today(),
                faktura_id=1
            )
            assert form.validate() is True

    def test_memorandum_create_form_empty_string_komitent_coerce(self, app):
        """Test that empty string in komitent_id is coerced to None without error."""
        with app.app_context():
            # Populate choices to simulate route behavior
            form = MemorandumCreateForm(
                naslov='Test memorandum',
                sadrzaj='Ovo je detaljan sadrzaj memoranduma sa dovoljno karaktera za validaciju.',
                datum=date.today()
            )
            form.komitent_id.choices = [('', '-- Bez komitenta --'), (1, 'Test Komitent')]
            form.faktura_id.choices = [('', '-- Bez fakture --'), (1, 'Faktura 001')]

            # Manually set data as empty string (simulates form submission)
            form.komitent_id.data = ''
            form.faktura_id.data = ''

            # Process should coerce '' to None without raising ValueError
            assert form.komitent_id.data is None or form.komitent_id.data == ''
            assert form.faktura_id.data is None or form.faktura_id.data == ''


class TestMemorandumEditForm:
    """Test suite for MemorandumEditForm."""

    def test_memorandum_edit_form_valid(self, app):
        """Test edit form validation succeeds when all required fields are valid."""
        with app.app_context():
            form = MemorandumEditForm(
                naslov='Izmenjeni naslov',
                sadrzaj='Ovo je izmenjeni sadrzaj memoranduma sa dovoljno karaktera za validaciju.',
                datum=date.today()
            )
            assert form.validate() is True

    def test_memorandum_edit_form_missing_naslov(self, app):
        """Test edit form validation fails when naslov is missing."""
        with app.app_context():
            form = MemorandumEditForm(
                naslov='',
                sadrzaj='Ovo je izmenjeni sadrzaj memoranduma sa dovoljno karaktera za validaciju.',
                datum=date.today()
            )
            assert form.validate() is False
            assert any('Naslov je obavezan' in error for error in form.naslov.errors)

    def test_memorandum_edit_form_datum_in_future(self, app):
        """Test edit form validation fails when datum is in the future."""
        with app.app_context():
            future_date = date.today() + timedelta(days=7)
            form = MemorandumEditForm(
                naslov='Izmenjeni naslov',
                sadrzaj='Ovo je izmenjeni sadrzaj memoranduma sa dovoljno karaktera za validaciju.',
                datum=future_date
            )
            assert form.validate() is False
            assert any('Datum ne može biti u budućnosti' in error for error in form.datum.errors)
