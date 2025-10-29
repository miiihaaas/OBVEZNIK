"""Forms for Komitent Management (CRUD)."""
from flask_wtf import FlaskForm
from wtforms import StringField, HiddenField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, ValidationError, Length, Regexp, Optional
from app.models.komitent import Komitent
from flask_login import current_user
import re


class DinarskiRacunForm(FlaskForm):
    """Sub-form for dinarski račun (bank account)."""
    banka = StringField(
        'Banka',
        validators=[DataRequired(message='Banka je obavezna.')],
        render_kw={'class': 'form-control', 'placeholder': 'Naziv banke'}
    )
    racun = StringField(
        'Broj računa',
        validators=[DataRequired(message='Broj računa je obavezan.')],
        render_kw={'class': 'form-control', 'placeholder': '###-###########-##'}
    )


class DevizniRacunForm(FlaskForm):
    """Sub-form for devizni račun (foreign currency account)."""
    banka = StringField(
        'Banka',
        validators=[Optional()],
        render_kw={'class': 'form-control', 'placeholder': 'Naziv banke'}
    )
    iban = StringField(
        'IBAN',
        validators=[Optional()],
        render_kw={'class': 'form-control', 'placeholder': 'RS35260005601001611379'}
    )
    swift = StringField(
        'SWIFT',
        validators=[Optional()],
        render_kw={'class': 'form-control', 'placeholder': 'BEOBBGRXXX'}
    )
    valuta = SelectField(
        'Valuta',
        choices=[('EUR', 'EUR'), ('USD', 'USD'), ('GBP', 'GBP'), ('CHF', 'CHF')],
        validators=[Optional()],
        render_kw={'class': 'form-control'}
    )


def validate_email_format(form, field):
    """
    Custom email format validator using regex pattern.

    This provides additional validation beyond the Email() validator
    to ensure email format compliance with standard patterns.

    Args:
        form: The form instance
        field: Email field to validate

    Raises:
        ValidationError: If email format is invalid
    """
    if field.data:
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(field.data):
            raise ValidationError('Unesite ispravnu email adresu.')


class KomitentCreateForm(FlaskForm):
    """Form for creating a new Komitent."""

    pib = StringField(
        'PIB',
        validators=[
            DataRequired(message='PIB je obavezan.'),
            Length(min=8, max=9, message='PIB mora imati 8 ili 9 cifara.'),
            Regexp(r'^\d{8,9}$', message='PIB mora biti 8 ili 9 cifara.')
        ],
        render_kw={'class': 'form-control', 'placeholder': '12345678'}
    )

    naziv = StringField(
        'Naziv',
        validators=[
            DataRequired(message='Naziv je obavezan.'),
            Length(max=255, message='Naziv može imati maksimalno 255 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Naziv komitenta'}
    )

    maticni_broj = StringField(
        'Matični broj',
        validators=[
            DataRequired(message='Matični broj je obavezan.'),
            Length(min=8, max=8, message='Matični broj mora imati tačno 8 cifara.')
        ],
        render_kw={'class': 'form-control', 'placeholder': '12345678'}
    )

    adresa = StringField(
        'Ulica',
        validators=[
            DataRequired(message='Ulica je obavezna.'),
            Length(max=255, message='Ulica može imati maksimalno 255 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Naziv ulice'}
    )

    broj = StringField(
        'Broj',
        validators=[
            DataRequired(message='Broj je obavezan.'),
            Length(max=20, message='Broj može imati maksimalno 20 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Kućni broj'}
    )

    postanski_broj = StringField(
        'Poštanski broj',
        validators=[
            DataRequired(message='Poštanski broj je obavezan.'),
            Length(max=10, message='Poštanski broj može imati maksimalno 10 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': '11000'}
    )

    mesto = StringField(
        'Mesto',
        validators=[
            DataRequired(message='Mesto je obavezno.'),
            Length(max=100, message='Mesto može imati maksimalno 100 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Beograd'}
    )

    drzava = StringField(
        'Država',
        validators=[
            DataRequired(message='Država je obavezna.'),
            Length(max=50, message='Država može imati maksimalno 50 karaktera.')
        ],
        default='Srbija',
        render_kw={'class': 'form-control', 'placeholder': 'Srbija'}
    )

    email = StringField(
        'Email',
        validators=[
            DataRequired(message='Email je obavezan.'),
            Email(message='Unesite ispravnu email adresu.'),
            Length(max=120, message='Email može imati maksimalno 120 karaktera.'),
            validate_email_format
        ],
        render_kw={'class': 'form-control', 'placeholder': 'komitent@primer.rs'}
    )

    # Dinarski računi (JSON list)
    dinarski_racuni_json = HiddenField('Dinarski računi')

    # Devizni računi (JSON list)
    devizni_racuni_json = HiddenField('Devizni računi')

    kontakt_osoba = StringField(
        'Kontakt Osoba',
        validators=[
            Optional(),
            Length(max=255, message='Kontakt osoba može imati maksimalno 255 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Ime i prezime kontakt osobe (opciono)'}
    )

    napomene = TextAreaField(
        'Dodatne Napomene',
        validators=[Optional()],
        render_kw={'class': 'form-control', 'rows': 4, 'placeholder': 'Dodatne napomene o komitentu (opciono)'}
    )

    def validate_pib(self, field):
        """
        Check that PIB is unique within the firma.

        Args:
            field: PIB field to validate

        Raises:
            ValidationError: If PIB already exists for this firma
        """
        # Get firma_id from current_user (pausalac) or from hidden field (admin)
        firma_id = current_user.firma_id if current_user.firma_id else None

        if firma_id:
            # Check if PIB already exists for this firma
            existing = Komitent.query.filter_by(
                firma_id=firma_id,
                pib=field.data
            ).first()

            if existing:
                raise ValidationError('Komitent sa ovim PIB-om već postoji u vašoj firmi.')


class KomitentEditForm(FlaskForm):
    """Form for editing an existing Komitent."""

    pib = StringField(
        'PIB',
        validators=[
            DataRequired(message='PIB je obavezan.'),
            Length(min=8, max=9, message='PIB mora imati 8 ili 9 cifara.'),
            Regexp(r'^\d{8,9}$', message='PIB mora biti 8 ili 9 cifara.')
        ],
        render_kw={'class': 'form-control', 'readonly': True}
    )

    naziv = StringField(
        'Naziv',
        validators=[
            DataRequired(message='Naziv je obavezan.'),
            Length(max=255, message='Naziv može imati maksimalno 255 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Naziv komitenta'}
    )

    maticni_broj = StringField(
        'Matični broj',
        validators=[
            DataRequired(message='Matični broj je obavezan.'),
            Length(min=8, max=8, message='Matični broj mora imati tačno 8 cifara.')
        ],
        render_kw={'class': 'form-control', 'placeholder': '12345678'}
    )

    adresa = StringField(
        'Ulica',
        validators=[
            DataRequired(message='Ulica je obavezna.'),
            Length(max=255, message='Ulica može imati maksimalno 255 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Naziv ulice'}
    )

    broj = StringField(
        'Broj',
        validators=[
            DataRequired(message='Broj je obavezan.'),
            Length(max=20, message='Broj može imati maksimalno 20 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Kućni broj'}
    )

    postanski_broj = StringField(
        'Poštanski broj',
        validators=[
            DataRequired(message='Poštanski broj je obavezan.'),
            Length(max=10, message='Poštanski broj može imati maksimalno 10 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': '11000'}
    )

    mesto = StringField(
        'Mesto',
        validators=[
            DataRequired(message='Mesto je obavezno.'),
            Length(max=100, message='Mesto može imati maksimalno 100 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Beograd'}
    )

    drzava = StringField(
        'Država',
        validators=[
            DataRequired(message='Država je obavezna.'),
            Length(max=50, message='Država može imati maksimalno 50 karaktera.')
        ],
        default='Srbija',
        render_kw={'class': 'form-control', 'placeholder': 'Srbija'}
    )

    email = StringField(
        'Email',
        validators=[
            DataRequired(message='Email je obavezan.'),
            Email(message='Unesite ispravnu email adresu.'),
            Length(max=120, message='Email može imati maksimalno 120 karaktera.'),
            validate_email_format
        ],
        render_kw={'class': 'form-control', 'placeholder': 'komitent@primer.rs'}
    )

    # Dinarski računi (JSON list)
    dinarski_racuni_json = HiddenField('Dinarski računi')

    # Devizni računi (JSON list)
    devizni_racuni_json = HiddenField('Devizni računi')

    kontakt_osoba = StringField(
        'Kontakt Osoba',
        validators=[
            Optional(),
            Length(max=255, message='Kontakt osoba može imati maksimalno 255 karaktera.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Ime i prezime kontakt osobe (opciono)'}
    )

    napomene = TextAreaField(
        'Dodatne Napomene',
        validators=[Optional()],
        render_kw={'class': 'form-control', 'rows': 4, 'placeholder': 'Dodatne napomene o komitentu (opciono)'}
    )
