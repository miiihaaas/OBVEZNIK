"""
Custom WTForms validators for application security.

Story 5.8 - Security Audit & Production Hardening
Task 7 - Password Policy Enforcement
"""
import re
from wtforms import ValidationError


def validate_password_strength(form, field):
    """
    Validate password strength according to security policy.

    Requirements:
    - Minimum 8 characters
    - At least 1 number (0-9)

    Args:
        form: WTForms form object
        field: Password field being validated

    Raises:
        ValidationError: If password does not meet requirements

    Example usage:
        class RegistrationForm(FlaskForm):
            password = PasswordField('Lozinka', validators=[
                DataRequired(),
                validate_password_strength
            ])
    """
    password = field.data

    # Check minimum length
    if len(password) < 8:
        raise ValidationError('Lozinka mora imati najmanje 8 karaktera.')

    # Check for at least one number
    if not re.search(r'\d', password):
        raise ValidationError('Lozinka mora sadržati bar jedan broj (0-9).')

    # Optional: Additional requirements (commented out for MVP)
    # Uncomment if stronger password policy is needed

    # if not re.search(r'[A-Z]', password):
    #     raise ValidationError('Lozinka mora sadržati bar jedno veliko slovo (A-Z).')

    # if not re.search(r'[a-z]', password):
    #     raise ValidationError('Lozinka mora sadržati bar jedno malo slovo (a-z).')

    # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
    #     raise ValidationError('Lozinka mora sadržati bar jedan specijalni karakter (!@#$%^&*...).')


def validate_pib(form, field):
    """
    Validate Serbian PIB (Poreski Identifikacioni Broj).

    Requirements:
    - Must be 8 or 9 digits
    - Only numeric characters

    Args:
        form: WTForms form object
        field: PIB field being validated

    Raises:
        ValidationError: If PIB is not valid

    Example usage:
        class FirmaForm(FlaskForm):
            pib = StringField('PIB', validators=[
                DataRequired(),
                validate_pib
            ])
    """
    pib = field.data

    # Remove whitespace
    pib = pib.strip()

    # Check if only digits
    if not pib.isdigit():
        raise ValidationError('PIB mora sadržati samo brojeve.')

    # Check length (8 or 9 digits)
    if len(pib) not in [8, 9]:
        raise ValidationError('PIB mora imati 8 ili 9 cifara.')


def validate_matični_broj(form, field):
    """
    Validate Serbian Matični broj (Company Registration Number).

    Requirements:
    - Must be exactly 8 digits
    - Only numeric characters

    Args:
        form: WTForms form object
        field: Matični broj field being validated

    Raises:
        ValidationError: If Matični broj is not valid

    Example usage:
        class FirmaForm(FlaskForm):
            matični_broj = StringField('Matični broj', validators=[
                DataRequired(),
                validate_matični_broj
            ])
    """
    matični_broj = field.data

    # Remove whitespace
    matični_broj = matični_broj.strip()

    # Check if only digits
    if not matični_broj.isdigit():
        raise ValidationError('Matični broj mora sadržati samo brojeve.')

    # Check length (exactly 8 digits)
    if len(matični_broj) != 8:
        raise ValidationError('Matični broj mora imati tačno 8 cifara.')
