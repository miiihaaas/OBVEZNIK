"""Forms for Faktura Management (Invoice CRUD)."""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, IntegerField, DateField, SelectField,
    DecimalField, HiddenField, FieldList, FormField
)
from wtforms.validators import (
    DataRequired, Optional, Length, NumberRange,
    Regexp, ValidationError
)
from datetime import date
from flask_login import current_user
from app.models.komitent import Komitent
from app.utils.query_helpers import filter_by_firma


class OptionalDecimalField(DecimalField):
    """
    DecimalField that accepts empty strings without validation errors.

    Empty strings are converted to None during processing, allowing
    the field to be optional without triggering 'Not a valid decimal value' errors.
    """

    def process_formdata(self, valuelist):
        """
        Process form data, converting empty strings to None.

        Args:
            valuelist: List of values from form submission
        """
        if valuelist:
            # If empty string, set to None (will be accepted)
            if valuelist[0] == '' or valuelist[0] is None:
                self.data = None
                return
        # Otherwise, use parent's process_formdata
        super().process_formdata(valuelist)


class RequiredForDevizna:
    """
    Custom validator that requires a field to be filled for devizna fakture.

    This validator checks the tip_fakture field and raises ValidationError
    if the field is empty/None when tip_fakture is 'devizna'.
    """

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        """
        Validate that field has a value when tip_fakture is 'devizna'.

        Args:
            form: Parent form instance
            field: Field being validated

        Raises:
            ValidationError: If devizna faktura and field is empty
        """
        if hasattr(form, 'tip_fakture') and form.tip_fakture.data == 'devizna':
            if not field.data or field.data <= 0:
                message = self.message or f'{field.label.text} je obavezan za devizne fakture.'
                raise ValidationError(message)


class FakturaStavkaForm(FlaskForm):
    """Form for a single faktura line item (stavka)."""

    artikal_id = IntegerField(
        'Artikal ID',
        validators=[Optional()],
        render_kw={'class': 'form-control artikal-id-input', 'type': 'hidden'}
    )

    naziv = StringField(
        'Naziv',
        validators=[
            DataRequired(message='Naziv stavke je obavezan.'),
            Length(max=255, message='Naziv može imati maksimalno 255 karaktera.')
        ],
        render_kw={'class': 'form-control naziv-input', 'placeholder': 'Naziv usluge/proizvoda'}
    )

    kolicina = DecimalField(
        'Količina',
        validators=[
            DataRequired(message='Količina je obavezna.'),
            NumberRange(min=0.01, message='Količina mora biti veća od 0.')
        ],
        places=2,
        render_kw={'class': 'form-control kolicina-input', 'placeholder': '1.00', 'step': '0.01'}
    )

    jedinica_mere = StringField(
        'Jedinica mere',
        validators=[
            DataRequired(message='Jedinica mere je obavezna.'),
            Length(max=20, message='Jedinica mere može imati maksimalno 20 karaktera.')
        ],
        render_kw={'class': 'form-control jedinica-input', 'placeholder': 'kom, h, m2...'}
    )

    cena = DecimalField(
        'Cena po jedinici',
        validators=[
            DataRequired(message='Cena je obavezna.'),
            NumberRange(min=0.01, message='Cena mora biti veća od 0.')
        ],
        places=2,
        render_kw={'class': 'form-control cena-input', 'placeholder': '0.00', 'step': '0.01'}
    )

    ukupno = DecimalField(
        'Ukupno',
        validators=[Optional()],
        places=2,
        render_kw={'class': 'form-control ukupno-input', 'readonly': True, 'placeholder': '0.00'}
    )

    redni_broj = IntegerField(
        'Redni broj',
        validators=[Optional()],
        render_kw={'class': 'form-control redni-broj-input', 'type': 'hidden'}
    )

    class Meta:
        csrf = False  # CSRF je već uključen u parent formu


class FakturaCreateForm(FlaskForm):
    """Form for creating a new invoice (faktura)."""

    tip_fakture = SelectField(
        'Tip fakture',
        choices=[
            ('standardna', 'Domaća (RSD)'),
            ('profaktura', 'Profaktura'),
            ('avansna', 'Avansna'),
            ('devizna', 'Devizna (EUR/USD/GBP/CHF)')
        ],
        default='standardna',
        validators=[DataRequired(message='Tip fakture je obavezan.')],
        render_kw={'class': 'form-control'}
    )

    komitent_id = IntegerField(
        'Komitent',
        validators=[DataRequired(message='Komitent je obavezan.')],
        render_kw={'class': 'form-control komitent-select', 'type': 'hidden'}
    )

    datum_prometa = DateField(
        'Datum prometa',
        validators=[DataRequired(message='Datum prometa je obavezan.')],
        default=date.today,
        format='%Y-%m-%d',
        render_kw={'class': 'form-control', 'type': 'date'}
    )

    # Foreign currency fields (conditional - only for devizna fakture)
    valuta_fakture = SelectField(
        'Valuta fakture',
        choices=[
            ('', 'Izaberite valutu...'),
            ('EUR', 'EUR - Euro'),
            ('USD', 'USD - Američki dolar'),
            ('GBP', 'GBP - Britanska funta'),
            ('CHF', 'CHF - Švajcarski franak')
        ],
        default='',
        validators=[],  # Conditional validation handled by validate_valuta_fakture() method
        render_kw={'class': 'form-control'}
    )

    srednji_kurs = DecimalField(
        'Srednji kurs NBS',
        validators=[
            Optional(),  # Allow empty values for non-devizna fakture
            RequiredForDevizna(message='Srednji kurs NBS je obavezan za devizne fakture i mora biti veći od 0.')
        ],
        places=4,
        render_kw={'class': 'form-control', 'placeholder': '0.0000', 'step': '0.0001'}
    )

    valuta_placanja = IntegerField(
        'Valuta plaćanja (dani)',
        validators=[
            DataRequired(message='Valuta plaćanja je obavezna.'),
            NumberRange(min=1, max=365, message='Valuta plaćanja mora biti između 1 i 365 dana.')
        ],
        default=7,
        render_kw={'class': 'form-control', 'placeholder': '7'}
    )

    # Optional reference fields
    broj_ugovora = StringField(
        'Broj ugovora',
        validators=[
            Optional(),
            Length(max=100, message='Broj ugovora može imati maksimalno 100 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Opciono'}
    )

    broj_odluke = StringField(
        'Broj odluke',
        validators=[
            Optional(),
            Length(max=100, message='Broj odluke može imati maksimalno 100 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Opciono'}
    )

    broj_narudzbenice = StringField(
        'Broj narudžbenice/ponude',
        validators=[
            Optional(),
            Length(max=100, message='Broj narudžbenice može imati maksimalno 100 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Opciono'}
    )

    poziv_na_broj = StringField(
        'Poziv na broj',
        validators=[
            Optional(),
            Regexp(r'^(95|97)', message='Poziv na broj mora početi sa 95 ili 97.'),
            Length(max=50, message='Poziv na broj može imati maksimalno 50 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': '95 ili 97...'}
    )

    model = StringField(
        'Model',
        validators=[
            Optional(),
            Length(max=10, message='Model može imati maksimalno 10 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Opciono'}
    )

    # Dynamic list of line items
    stavke = FieldList(
        FormField(FakturaStavkaForm),
        min_entries=1,
        max_entries=100
    )

    def validate_komitent_id(self, field):
        """
        Validate that komitent exists and belongs to current user's firma.

        Args:
            field: komitent_id field to validate

        Raises:
            ValidationError: If komitent doesn't exist or doesn't belong to firma

        Note:
            MAINT-001: Devizni račun validation moved to service layer to avoid duplication
        """
        if not field.data:
            raise ValidationError('Komitent je obavezan.')

        # Get komitent with tenant isolation
        komitent = filter_by_firma(Komitent.query).filter_by(id=field.data).first()

        if not komitent:
            raise ValidationError('Izabrani komitent ne postoji ili ne pripada vašoj firmi.')

    def validate_stavke(self, field):
        """
        Validate that at least one valid line item exists.

        Args:
            field: stavke field to validate

        Raises:
            ValidationError: If no valid line items exist
        """
        if not field.data or len(field.data) == 0:
            raise ValidationError('Mora postojati bar jedna stavka fakture.')

        # Check that at least one stavka has data
        has_valid_stavka = False
        for stavka in field.data:
            if stavka.get('naziv') and stavka.get('kolicina') and stavka.get('cena'):
                has_valid_stavka = True
                break

        if not has_valid_stavka:
            raise ValidationError('Mora postojati bar jedna popunjena stavka fakture.')

    def validate_valuta_fakture(self, field):
        """
        Validate that valuta_fakture is required for devizna fakture.

        Args:
            field: valuta_fakture field to validate

        Raises:
            ValidationError: If devizna faktura doesn't have valuta or
                            if non-devizna faktura has valuta
        """
        if self.tip_fakture.data == 'devizna':
            if not field.data or field.data == '':
                raise ValidationError('Valuta fakture je obavezna za devizne fakture.')
        else:
            if field.data and field.data != '':
                raise ValidationError('Valuta fakture može biti izabrana samo za devizne fakture.')

