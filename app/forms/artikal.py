"""Forms for Artikal Management (CRUD)."""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, ValidationError
from decimal import Decimal


def validate_cena_minimum(form, field):
    """
    Custom validator for podrazumevana_cena field.

    Ensures that if a price is provided, it must be at least 0.01.
    Handles the case where Decimal(0) is falsy and Optional() would skip validation.

    Args:
        form: The form instance
        field: The cena field to validate

    Raises:
        ValidationError: If price is 0 or negative (< 0.01)
    """
    # Allow None or empty (optional field)
    if field.data is None or field.data == '':
        return

    # If price is provided, it must be > 0
    if field.data <= Decimal('0.00'):
        raise ValidationError('Cena mora biti najmanje 0.01 RSD.')


# Jedinica mere choices (AC: 4)
JEDINICA_MERE_CHOICES = [
    ('sat', 'sat'),
    ('dan', 'dan'),
    ('kom', 'kom'),
    ('kg', 'kg'),
    ('m', 'm'),
    ('m²', 'm²'),
    ('m³', 'm³'),
    ('l', 'l'),
    ('usluga', 'usluga')
]


class ArtikalCreateForm(FlaskForm):
    """Form for creating a new Artikal."""

    naziv = StringField(
        'Naziv artikla',
        validators=[
            DataRequired(message='Naziv je obavezan.'),
            Length(max=255, message='Naziv može imati maksimalno 255 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Naziv artikla ili usluge'}
    )

    opis = TextAreaField(
        'Opis',
        validators=[Optional()],
        render_kw={'class': 'form-control', 'rows': 3, 'placeholder': 'Detaljan opis artikla ili usluge (opciono)'}
    )

    podrazumevana_cena = DecimalField(
        'Podrazumevana cena (RSD)',
        validators=[validate_cena_minimum],
        places=2,
        render_kw={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01', 'min': '0.01'}
    )

    jedinica_mere = SelectField(
        'Jedinica mere',
        choices=JEDINICA_MERE_CHOICES,
        validators=[DataRequired(message='Jedinica mere je obavezna.')],
        render_kw={'class': 'form-select'}
    )

    submit = SubmitField('Sačuvaj Artikal')


class ArtikalEditForm(FlaskForm):
    """Form for editing an existing Artikal."""

    naziv = StringField(
        'Naziv artikla',
        validators=[
            DataRequired(message='Naziv je obavezan.'),
            Length(max=255, message='Naziv može imati maksimalno 255 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Naziv artikla ili usluge'}
    )

    opis = TextAreaField(
        'Opis',
        validators=[Optional()],
        render_kw={'class': 'form-control', 'rows': 3, 'placeholder': 'Detaljan opis artikla ili usluge (opciono)'}
    )

    podrazumevana_cena = DecimalField(
        'Podrazumevana cena (RSD)',
        validators=[validate_cena_minimum],
        places=2,
        render_kw={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01', 'min': '0.01'}
    )

    jedinica_mere = SelectField(
        'Jedinica mere',
        choices=JEDINICA_MERE_CHOICES,
        validators=[DataRequired(message='Jedinica mere je obavezna.')],
        render_kw={'class': 'form-select'}
    )

    submit = SubmitField('Sačuvaj Izmene')
