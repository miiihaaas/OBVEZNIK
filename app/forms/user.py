"""Forms for User Management (Admin CRUD)."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email, ValidationError, Optional
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma


class UserCreateForm(FlaskForm):
    """Form for creating a new user."""

    full_name = StringField(
        'Ime i Prezime',
        validators=[DataRequired(message='Ime i prezime su obavezni.')],
        render_kw={'class': 'form-control', 'placeholder': 'Unesite ime i prezime'}
    )

    email = StringField(
        'Email',
        validators=[
            DataRequired(message='Email je obavezan.'),
            Email(message='Unesite ispravnu email adresu.')
        ],
        render_kw={'class': 'form-control', 'placeholder': 'primer@email.com'}
    )

    password = PasswordField(
        'Lozinka',
        validators=[DataRequired(message='Lozinka je obavezna.')],
        render_kw={'class': 'form-control', 'placeholder': 'Unesite lozinku'}
    )

    role = SelectField(
        'Tip Korisnika',
        choices=[('admin', 'Admin'), ('pausalac', 'Paušalac')],
        validators=[DataRequired(message='Tip korisnika je obavezan.')],
        render_kw={'class': 'form-select'}
    )

    firma_id = SelectField(
        'Paušalna Firma',
        coerce=int,
        validators=[Optional()],
        render_kw={'class': 'form-select'}
    )

    def validate_email(self, field):
        """
        Check if email already exists in database.

        Args:
            field: Email field to validate

        Raises:
            ValidationError: If email already exists
        """
        user = User.query.filter_by(email=field.data).first()
        if user:
            raise ValidationError('Email je već registrovan.')

    def validate_firma_id(self, field):
        """
        Require firma_id for pausalac role.

        Args:
            field: Firma_id field to validate

        Raises:
            ValidationError: If firma_id is missing for pausalac role
        """
        # Check if role is pausalac and firma_id is not set (0 or None)
        if self.role.data == 'pausalac':
            if field.data is None or field.data == 0 or not field.data:
                raise ValidationError('Morate izabrati paušalnu firmu za paušalac korisnika.')


class UserEditForm(UserCreateForm):
    """
    Form for editing an existing user.

    Allows same email for current user and makes password optional.
    """

    password = PasswordField(
        'Nova Lozinka (opciono)',
        validators=[Optional()],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Ostavite prazno da zadržite postojeću lozinku'
        }
    )

    def __init__(self, original_email, *args, **kwargs):
        """
        Initialize edit form with original email.

        Args:
            original_email: Current email of user being edited
        """
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, field):
        """
        Allow same email for current user.

        Args:
            field: Email field to validate

        Raises:
            ValidationError: If email exists for a different user
        """
        if field.data != self.original_email:
            user = User.query.filter_by(email=field.data).first()
            if user:
                raise ValidationError('Email je već registrovan.')
