"""Forms for Faktura Management (Invoice CRUD)."""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, IntegerField, DateField, SelectField,
    DecimalField, HiddenField, FieldList, FormField, BooleanField
)
from wtforms.validators import (
    DataRequired, Optional, Length, NumberRange,
    Regexp, ValidationError
)
from datetime import date
from flask_login import current_user
from app import db
from app.models.komitent import Komitent
from app.models.faktura import Faktura
from app.utils.query_helpers import filter_by_firma


def coerce_int_or_none(value):
    """
    Custom coerce function for SelectField that allows empty string to become None.

    Used for optional SelectField with coerce=int where empty choice is valid.

    Args:
        value: Value from form (string or None)

    Returns:
        int or None: Coerced value
    """
    if value in ('', None):
        return None
    return int(value)


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

    srednji_kurs = OptionalDecimalField(
        'Srednji kurs NBS',
        validators=[
            RequiredForDevizna(message='Srednji kurs NBS je obavezan za devizne fakture i mora biti veći od 0.')
        ],
        places=4,
        render_kw={'class': 'form-control', 'placeholder': '0.0000', 'step': '0.0001'}
    )

    # Avansna faktura fields (conditional - only for avansna fakture - Story 4.3)
    ukupna_vrednost_posla = OptionalDecimalField(
        'Ukupna vrednost posla',
        validators=[Optional()],
        places=2,
        render_kw={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}
    )

    procenat_avansa = IntegerField(
        'Procenat avansa (%)',
        validators=[
            Optional(),
            NumberRange(min=1, max=100, message='Procenat avansa mora biti između 1 i 100.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Npr. 30'}
    )

    opis_posla = StringField(
        'Opis posla',
        validators=[
            Optional(),
            Length(max=255, message='Opis posla može imati maksimalno 255 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Naziv projekta ili posla'}
    )

    # Story 4.4: Zatvaranje avansa fields
    zatvara_avans = BooleanField(
        'Zatvara avans',
        default=False,
        validators=[Optional()],
        render_kw={'class': 'form-check-input'}
    )

    avansna_faktura_id = SelectField(
        'Izaberi avansnu fakturu',
        coerce=coerce_int_or_none,
        choices=[],  # Dynamic choices via AJAX
        validators=[Optional()],
        render_kw={'class': 'form-control avansna-select'}
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

    def validate_ukupna_vrednost_posla(self, field):
        """
        Validate that ukupna_vrednost_posla is required when procenat_avansa is entered.

        Args:
            field: ukupna_vrednost_posla field to validate

        Raises:
            ValidationError: If procenat_avansa is entered but ukupna_vrednost_posla is not
        """
        if self.tip_fakture.data == 'avansna' and self.procenat_avansa.data:
            if not field.data or field.data <= 0:
                raise ValidationError(
                    'Ukupna vrednost posla je obavezna kada je procenat avansa unet.'
                )

    def validate_avansna_faktura_id(self, field):
        """
        Validate avansna faktura selection when zatvara_avans is checked.

        Args:
            field: avansna_faktura_id field to validate

        Raises:
            ValidationError: If avansna faktura is invalid or already closed

        Business Rules:
            - Required when zatvara_avans is checked
            - Must belong to current user's firma (SEC-001: Tenant isolation)
            - Must have status='izdata' (not 'draft', 'zatvorena', etc.)
            - Must be tip_fakture='avansna'
        """
        if self.zatvara_avans.data:
            if not field.data:
                raise ValidationError("Izaberite avansnu fakturu koju želite zatvoriti.")

            # Load avansna faktura
            avansna = db.session.get(Faktura, field.data)
            if not avansna:
                raise ValidationError("Izabrana avansna faktura nije pronađena.")

            # SEC-001: Tenant isolation
            if avansna.firma_id != current_user.firma.id:
                raise ValidationError("Avansna faktura ne pripada vašoj firmi.")

            # Validation: Must be tip_fakture='avansna'
            if avansna.tip_fakture != 'avansna':
                raise ValidationError("Izabrana faktura nije avansna faktura.")

            # Validation: Must be 'izdata', not 'zatvorena'
            if avansna.status == 'zatvorena':
                raise ValidationError(f"Avansna faktura {avansna.broj_fakture} je već zatvorena.")

            if avansna.status != 'izdata':
                raise ValidationError("Samo izdate avansne fakture mogu biti zatvorene.")

