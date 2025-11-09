"""Forms for Memorandum Management (CRUD)."""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from datetime import date


def coerce_int_or_none(value):
    """
    Coerce value to int or None for SelectField.

    Handles empty strings and None values that should map to NULL in database.

    Args:
        value: The value to coerce (can be '', None, or string representation of int)

    Returns:
        int or None: Converted integer or None for empty values
    """
    if value in ('', None):
        return None
    return int(value)


def validate_naslov_minimum(form, field):
    """
    Custom validator for naslov field.

    Ensures naslov has at least 3 characters.

    Args:
        form: The form instance
        field: The naslov field to validate

    Raises:
        ValidationError: If naslov is too short (< 3 chars)
    """
    if field.data and len(field.data.strip()) < 3:
        raise ValidationError('Naslov mora imati najmanje 3 karaktera.')


def validate_sadrzaj_minimum(form, field):
    """
    Custom validator for sadrzaj field.

    Ensures sadrzaj has at least 10 characters for meaningful content.

    Args:
        form: The form instance
        field: The sadrzaj field to validate

    Raises:
        ValidationError: If sadrzaj is too short (< 10 chars)
    """
    if field.data and len(field.data.strip()) < 10:
        raise ValidationError('Sadržaj mora imati najmanje 10 karaktera.')


def validate_datum_not_future(form, field):
    """
    Custom validator for datum field.

    Ensures datum is not in the future.

    Args:
        form: The form instance
        field: The datum field to validate

    Raises:
        ValidationError: If datum is in the future
    """
    if field.data and field.data > date.today():
        raise ValidationError('Datum ne može biti u budućnosti.')


class MemorandumCreateForm(FlaskForm):
    """Form for creating a new Memorandum."""

    naslov = StringField(
        'Naslov',
        validators=[
            DataRequired(message='Naslov je obavezan.'),
            Length(min=3, max=255, message='Naslov mora imati između 3 i 255 karaktera.'),
            validate_naslov_minimum
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Unesite naslov memoranduma'}
    )

    sadrzaj = TextAreaField(
        'Sadržaj',
        validators=[
            DataRequired(message='Sadržaj je obavezan.'),
            validate_sadrzaj_minimum
        ],
        render_kw={'class': 'form-control', 'rows': 6, 'placeholder': 'Unesite sadržaj memoranduma (opisi poslova, napomene, ugovori, itd.)'}
    )

    datum = DateField(
        'Datum',
        format='%Y-%m-%d',
        validators=[
            DataRequired(message='Datum je obavezan.'),
            validate_datum_not_future
        ],
        default=date.today,
        render_kw={'class': 'form-control', 'type': 'date'}
    )

    komitent_id = SelectField(
        'Povezani komitent (opciono)',
        coerce=coerce_int_or_none,
        choices=[],
        validators=[Optional()],
        validate_choice=False,
        render_kw={'class': 'form-select'}
    )

    faktura_id = SelectField(
        'Povezana faktura (opciono)',
        coerce=coerce_int_or_none,
        choices=[],
        validators=[Optional()],
        validate_choice=False,
        render_kw={'class': 'form-select'}
    )

    submit = SubmitField('Sačuvaj Memorandum')


class MemorandumEditForm(FlaskForm):
    """Form for editing an existing Memorandum."""

    naslov = StringField(
        'Naslov',
        validators=[
            DataRequired(message='Naslov je obavezan.'),
            Length(min=3, max=255, message='Naslov mora imati između 3 i 255 karaktera.'),
            validate_naslov_minimum
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Unesite naslov memoranduma'}
    )

    sadrzaj = TextAreaField(
        'Sadržaj',
        validators=[
            DataRequired(message='Sadržaj je obavezan.'),
            validate_sadrzaj_minimum
        ],
        render_kw={'class': 'form-control', 'rows': 6, 'placeholder': 'Unesite sadržaj memoranduma (opisi poslova, napomene, ugovori, itd.)'}
    )

    datum = DateField(
        'Datum',
        format='%Y-%m-%d',
        validators=[
            DataRequired(message='Datum je obavezan.'),
            validate_datum_not_future
        ],
        render_kw={'class': 'form-control', 'type': 'date'}
    )

    komitent_id = SelectField(
        'Povezani komitent (opciono)',
        coerce=coerce_int_or_none,
        choices=[],
        validators=[Optional()],
        validate_choice=False,
        render_kw={'class': 'form-select'}
    )

    faktura_id = SelectField(
        'Povezana faktura (opciono)',
        coerce=coerce_int_or_none,
        choices=[],
        validators=[Optional()],
        validate_choice=False,
        render_kw={'class': 'form-select'}
    )

    submit = SubmitField('Sačuvaj Izmene')
