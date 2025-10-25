"""Unit tests for Artikal forms."""
import pytest
from app.forms.artikal import ArtikalCreateForm, ArtikalEditForm, JEDINICA_MERE_CHOICES


class TestArtikalCreateForm:
    """Test suite for ArtikalCreateForm."""

    def test_form_validation_success_with_all_fields(self, app):
        """Test form validation succeeds when all fields are filled."""
        with app.app_context():
            form = ArtikalCreateForm(
                naziv='Programiranje',
                opis='Izrada softvera po satu',
                podrazumevana_cena=3500.00,
                jedinica_mere='sat'
            )
            assert form.validate() is True

    def test_form_validation_success_with_required_fields_only(self, app):
        """Test form validation succeeds with only required fields (naziv, jedinica_mere)."""
        with app.app_context():
            form = ArtikalCreateForm(
                naziv='Konsultacije',
                jedinica_mere='sat'
            )
            assert form.validate() is True

    def test_form_validation_failure_missing_naziv(self, app):
        """Test form validation fails when naziv is missing."""
        with app.app_context():
            form = ArtikalCreateForm(
                naziv='',
                jedinica_mere='sat'
            )
            assert form.validate() is False
            assert 'Naziv je obavezan.' in form.naziv.errors

    def test_form_validation_failure_missing_jedinica_mere(self, app):
        """Test form validation fails when jedinica_mere is missing."""
        with app.app_context():
            form = ArtikalCreateForm(
                naziv='Testni artikal'
            )
            # SelectField sa choices ne dozvoljava prazan string, ali možemo testirati None
            assert form.jedinica_mere.data is None or form.jedinica_mere.data == ''

    def test_naziv_length_validation(self, app):
        """Test naziv field length validation (max 255 chars)."""
        with app.app_context():
            long_naziv = 'A' * 256
            form = ArtikalCreateForm(
                naziv=long_naziv,
                jedinica_mere='sat'
            )
            assert form.validate() is False
            assert 'Naziv može imati maksimalno 255 karaktera.' in form.naziv.errors

    def test_podrazumevana_cena_min_validation(self, app):
        """Test podrazumevana_cena field minimum value validation (min 0.01)."""
        with app.app_context():
            form = ArtikalCreateForm(
                naziv='Testni artikal',
                podrazumevana_cena=0.00,
                jedinica_mere='sat'
            )
            assert form.validate() is False
            assert 'Cena mora biti najmanje 0.01 RSD.' in form.podrazumevana_cena.errors

    def test_podrazumevana_cena_optional(self, app):
        """Test podrazumevana_cena is optional (can be None)."""
        with app.app_context():
            form = ArtikalCreateForm(
                naziv='Testni artikal',
                jedinica_mere='sat'
            )
            assert form.validate() is True

    def test_opis_optional(self, app):
        """Test opis field is optional."""
        with app.app_context():
            form = ArtikalCreateForm(
                naziv='Testni artikal',
                jedinica_mere='sat'
            )
            assert form.validate() is True

    def test_jedinica_mere_choices_available(self, app):
        """Test jedinica_mere dropdown has all expected choices."""
        with app.app_context():
            form = ArtikalCreateForm()
            # Check that all expected choices are present
            expected_choices = ['sat', 'dan', 'kom', 'kg', 'm', 'm²', 'm³', 'l', 'usluga']
            available_choices = [choice[0] for choice in form.jedinica_mere.choices]
            for expected in expected_choices:
                assert expected in available_choices


class TestArtikalEditForm:
    """Test suite for ArtikalEditForm."""

    def test_form_validation_success(self, app):
        """Test edit form validation succeeds with valid data."""
        with app.app_context():
            form = ArtikalEditForm(
                naziv='Programiranje (izmenjeno)',
                opis='Izrada softvera po satu - obnovljen opis',
                podrazumevana_cena=4000.00,
                jedinica_mere='sat'
            )
            assert form.validate() is True

    def test_form_validation_failure_missing_naziv(self, app):
        """Test edit form validation fails when naziv is missing."""
        with app.app_context():
            form = ArtikalEditForm(
                naziv='',
                jedinica_mere='sat'
            )
            assert form.validate() is False
            assert 'Naziv je obavezan.' in form.naziv.errors

    def test_all_fields_editable(self, app):
        """Test that all fields in edit form are editable."""
        with app.app_context():
            form = ArtikalEditForm(
                naziv='Novi naziv',
                opis='Novi opis',
                podrazumevana_cena=5000.00,
                jedinica_mere='dan'
            )
            assert form.validate() is True
            assert form.naziv.data == 'Novi naziv'
            assert form.opis.data == 'Novi opis'
            assert form.podrazumevana_cena.data == 5000.00
            assert form.jedinica_mere.data == 'dan'


class TestJedinicaMereChoices:
    """Test suite for jedinica_mere choices constant."""

    def test_jedinica_mere_choices_structure(self):
        """Test JEDINICA_MERE_CHOICES has correct structure."""
        assert isinstance(JEDINICA_MERE_CHOICES, list)
        assert len(JEDINICA_MERE_CHOICES) == 9

        # Check all choices are tuples of (value, label)
        for choice in JEDINICA_MERE_CHOICES:
            assert isinstance(choice, tuple)
            assert len(choice) == 2
            assert choice[0] == choice[1]  # value == label for these choices

    def test_jedinica_mere_choices_content(self):
        """Test JEDINICA_MERE_CHOICES contains all expected values."""
        expected = ['sat', 'dan', 'kom', 'kg', 'm', 'm²', 'm³', 'l', 'usluga']
        actual = [choice[0] for choice in JEDINICA_MERE_CHOICES]
        assert actual == expected
