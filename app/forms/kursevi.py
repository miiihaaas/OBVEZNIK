"""Forms for Kursevi (Exchange Rates) management."""
from flask_wtf import FlaskForm
from wtforms import SelectField, DecimalField, DateField
from wtforms.validators import DataRequired, NumberRange, ValidationError
from datetime import date


class KursManualOverrideForm(FlaskForm):
    """Form for manually overriding exchange rates."""

    valuta = SelectField(
        'Valuta',
        choices=[
            ('EUR', 'EUR - Evro'),
            ('USD', 'USD - Američki dolar'),
            ('GBP', 'GBP - Britanska funta'),
            ('CHF', 'CHF - Švajcarski franak')
        ],
        validators=[DataRequired(message='Valuta je obavezna.')]
    )

    kurs = DecimalField(
        'Srednji kurs',
        places=4,
        validators=[
            DataRequired(message='Kurs je obavezan.'),
            NumberRange(min=0.0001, max=9999.9999, message='Kurs mora biti između 0.0001 i 9999.9999.')
        ]
    )

    datum = DateField(
        'Datum',
        default=date.today,
        validators=[DataRequired(message='Datum je obavezan.')]
    )

    def validate_kurs(self, field):
        """Validate that kurs is positive and within reasonable range."""
        if field.data is None:
            raise ValidationError('Kurs je obavezan.')

        if field.data <= 0:
            raise ValidationError('Kurs mora biti veći od 0.')

        if field.data >= 1000:
            raise ValidationError('Kurs je previše visok. Proverite unos.')
