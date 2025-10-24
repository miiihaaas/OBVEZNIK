"""Forms for PausalnFirma Management (Admin CRUD)."""
from flask_wtf import FlaskForm
from wtforms import StringField, FieldList, FormField, HiddenField
from wtforms.validators import DataRequired, Email, ValidationError, Optional, Length, Regexp
from app.models.pausaln_firma import PausalnFirma
import re


class DinarskiRacunForm(FlaskForm):
    """Sub-form for dinarski račun (bank account)."""
    banka = StringField(
        'Banka',
        validators=[DataRequired(message='Banka je obavezna.')],
        render_kw={'class': 'form-control', 'placeholder': 'Naziv banke'}
    )
    broj = StringField(
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
        render_kw={'class': 'form-control', 'placeholder': 'RS##..'}
    )
    swift = StringField(
        'SWIFT',
        validators=[Optional()],
        render_kw={'class': 'form-control', 'placeholder': 'SWIFT kod'}
    )


class PausalnFirmaCreateForm(FlaskForm):
    """Form for creating a new PausalnFirma."""

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
        validators=[DataRequired(message='Naziv je obavezan.')],
        render_kw={'class': 'form-control', 'placeholder': 'Naziv firme'}
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
        validators=[DataRequired(message='Ulica je obavezna.')],
        render_kw={'class': 'form-control', 'placeholder': 'Naziv ulice'}
    )

    broj = StringField(
        'Broj',
        validators=[DataRequired(message='Broj je obavezan.')],
        render_kw={'class': 'form-control', 'placeholder': 'Kućni broj'}
    )

    postanski_broj = StringField(
        'Poštanski broj',
        validators=[DataRequired(message='Poštanski broj je obavezan.')],
        render_kw={'class': 'form-control', 'placeholder': '11000'}
    )

    mesto = StringField(
        'Mesto',
        validators=[DataRequired(message='Mesto je obavezno.')],
        render_kw={'class': 'form-control', 'placeholder': 'Beograd'}
    )

    drzava = StringField(
        'Država',
        validators=[DataRequired(message='Država je obavezna.')],
        default='Srbija',
        render_kw={'class': 'form-control', 'placeholder': 'Srbija'}
    )

    telefon = StringField(
        'Telefon',
        validators=[DataRequired(message='Telefon je obavezan.')],
        render_kw={'class': 'form-control', 'placeholder': '+381 11 1234567'}
    )

    email = StringField(
        'Email',
        validators=[
            Optional(),
            Email(message='Unesite ispravnu email adresu.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'firma@primer.rs'}
    )

    # Dinarski računi (JSON list)
    dinarski_racuni_json = HiddenField('Dinarski računi')

    # Devizni računi (JSON list)
    devizni_racuni_json = HiddenField('Devizni računi')

    prefiks_fakture = StringField(
        'Prefiks fakture',
        validators=[Optional(), Length(max=10, message='Prefiks može imati maksimalno 10 karaktera.')],
        render_kw={'class': 'form-control', 'placeholder': 'MRMR'}
    )

    sufiks_fakture = StringField(
        'Sufiks fakture',
        validators=[Optional(), Length(max=10, message='Sufiks može imati maksimalno 10 karaktera.')],
        render_kw={'class': 'form-control', 'placeholder': '/2025'}
    )

    pdv_kategorija = StringField(
        'PDV kategorija',
        default='SS',
        render_kw={'class': 'form-control', 'readonly': True}
    )

    sifra_osnova = StringField(
        'Šifra osnova',
        default='PDV-RS-33',
        render_kw={'class': 'form-control', 'readonly': True}
    )

    def validate_pib(self, field):
        """
        Check that PIB is unique.

        Args:
            field: PIB field to validate

        Raises:
            ValidationError: If PIB already exists
        """
        firma = PausalnFirma.query.filter_by(pib=field.data).first()
        if firma:
            raise ValidationError('Firma sa ovim PIB-om već postoji.')

    def validate_dinarski_racuni_json(self, field):
        """
        Validate that at least one dinarski račun is provided.

        Args:
            field: dinarski_racuni_json field to validate

        Raises:
            ValidationError: If no dinarski računi are provided
        """
        import json
        if not field.data:
            raise ValidationError('Morate uneti bar jedan dinarski račun.')

        try:
            racuni = json.loads(field.data)
            if not racuni or len(racuni) == 0:
                raise ValidationError('Morate uneti bar jedan dinarski račun.')
        except (ValueError, TypeError):
            raise ValidationError('Nevalidan format dinarskih računa.')

    def validate_email(self, field):
        """
        Validate email format using custom regex if email-validator fails.

        Args:
            field: Email field to validate

        Raises:
            ValidationError: If email format is invalid
        """
        if field.data:
            email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            if not email_pattern.match(field.data):
                raise ValidationError('Unesite ispravnu email adresu.')


class PausalnFirmaEditForm(FlaskForm):
    """Form for editing an existing PausalnFirma."""

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
        validators=[DataRequired(message='Naziv je obavezan.')],
        render_kw={'class': 'form-control', 'placeholder': 'Naziv firme'}
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
        validators=[DataRequired(message='Ulica je obavezna.')],
        render_kw={'class': 'form-control', 'placeholder': 'Naziv ulice'}
    )

    broj = StringField(
        'Broj',
        validators=[DataRequired(message='Broj je obavezan.')],
        render_kw={'class': 'form-control', 'placeholder': 'Kućni broj'}
    )

    postanski_broj = StringField(
        'Poštanski broj',
        validators=[DataRequired(message='Poštanski broj je obavezan.')],
        render_kw={'class': 'form-control', 'placeholder': '11000'}
    )

    mesto = StringField(
        'Mesto',
        validators=[DataRequired(message='Mesto je obavezno.')],
        render_kw={'class': 'form-control', 'placeholder': 'Beograd'}
    )

    drzava = StringField(
        'Država',
        validators=[DataRequired(message='Država je obavezna.')],
        default='Srbija',
        render_kw={'class': 'form-control', 'placeholder': 'Srbija'}
    )

    telefon = StringField(
        'Telefon',
        validators=[DataRequired(message='Telefon je obavezan.')],
        render_kw={'class': 'form-control', 'placeholder': '+381 11 1234567'}
    )

    email = StringField(
        'Email',
        validators=[
            Optional(),
            Email(message='Unesite ispravnu email adresu.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'firma@primer.rs'}
    )

    # Dinarski računi (JSON list)
    dinarski_racuni_json = HiddenField('Dinarski računi')

    # Devizni računi (JSON list)
    devizni_racuni_json = HiddenField('Devizni računi')

    prefiks_fakture = StringField(
        'Prefiks fakture',
        validators=[Optional(), Length(max=10, message='Prefiks može imati maksimalno 10 karaktera.')],
        render_kw={'class': 'form-control', 'placeholder': 'MRMR'}
    )

    sufiks_fakture = StringField(
        'Sufiks fakture',
        validators=[Optional(), Length(max=10, message='Sufiks može imati maksimalno 10 karaktera.')],
        render_kw={'class': 'form-control', 'placeholder': '/2025'}
    )

    pdv_kategorija = StringField(
        'PDV kategorija',
        default='SS',
        render_kw={'class': 'form-control', 'readonly': True}
    )

    sifra_osnova = StringField(
        'Šifra osnova',
        default='PDV-RS-33',
        render_kw={'class': 'form-control', 'readonly': True}
    )

    def validate_dinarski_racuni_json(self, field):
        """
        Validate that at least one dinarski račun is provided.

        Args:
            field: dinarski_racuni_json field to validate

        Raises:
            ValidationError: If no dinarski računi are provided
        """
        import json
        if not field.data:
            raise ValidationError('Morate uneti bar jedan dinarski račun.')

        try:
            racuni = json.loads(field.data)
            if not racuni or len(racuni) == 0:
                raise ValidationError('Morate uneti bar jedan dinarski račun.')
        except (ValueError, TypeError):
            raise ValidationError('Nevalidan format dinarskih računa.')

    def validate_email(self, field):
        """
        Validate email format using custom regex if email-validator fails.

        Args:
            field: Email field to validate

        Raises:
            ValidationError: If email format is invalid
        """
        if field.data:
            email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            if not email_pattern.match(field.data):
                raise ValidationError('Unesite ispravnu email adresu.')
