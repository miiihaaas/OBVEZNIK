"""Authentication forms for login and registration."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email


class LoginForm(FlaskForm):
    """Login form with email, password, and remember me checkbox."""

    email = StringField(
        'Email',
        validators=[DataRequired(message='Email je obavezan.'), Email(message='Unesite ispravnu email adresu.')],
        render_kw={'placeholder': 'unesite@email.com', 'class': 'form-control'}
    )

    password = PasswordField(
        'Lozinka',
        validators=[DataRequired(message='Lozinka je obavezna.')],
        render_kw={'placeholder': 'Unesite lozinku', 'class': 'form-control'}
    )

    remember_me = BooleanField(
        'Zapamti me',
        render_kw={'class': 'form-check-input'}
    )

    submit = SubmitField(
        'Prijavi se',
        render_kw={'class': 'btn btn-primary w-100'}
    )
