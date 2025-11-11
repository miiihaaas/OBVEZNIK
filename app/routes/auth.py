"""Authentication routes for login and logout."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db, limiter
from app.models.user import User
from app.forms.auth import LoginForm
from datetime import datetime, timezone
import logging

# Configure security logger
security_logger = logging.getLogger('security')

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per 15 minutes")  # Rate limit: max 5 login attempts per 15 minutes per IP
def login():
    """
    Login route.

    GET: Display login form
    POST: Process login credentials and authenticate user
    """
    # If user is already logged in, redirect to appropriate dashboard
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin_dashboard.dashboard'))
        else:
            return redirect(url_for('dashboard.pausalac_dashboard'))

    form = LoginForm()

    if form.validate_on_submit():
        # Query user by email
        user = User.query.filter_by(email=form.email.data).first()

        # Check if user exists and password is correct
        if user and user.check_password(form.password.data):
            # Check if user account is active
            if not user.is_active:
                # Log inactive account login attempt
                security_logger.warning(
                    f"Login attempt for inactive account: {form.email.data} from IP: {request.remote_addr}"
                )
                flash('Vaš nalog je deaktiviran. Kontaktirajte administratora.', 'danger')
                return render_template('auth/login.html', form=form)

            # Login user
            login_user(user, remember=form.remember_me.data)

            # Update last_login timestamp
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()

            # Log successful login
            security_logger.info(
                f"Successful login: user_id={user.id}, email={user.email}, "
                f"role={user.role}, ip={request.remote_addr}"
            )

            # Redirect to appropriate dashboard based on role
            if user.is_admin():
                return redirect(url_for('admin_dashboard.dashboard'))
            else:
                return redirect(url_for('dashboard.pausalac_dashboard'))
        else:
            # Log failed login attempt
            security_logger.warning(
                f"Failed login attempt: email={form.email.data}, ip={request.remote_addr}"
            )
            # Generic error message (don't reveal if email exists)
            flash('Invalid email or password', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """
    Logout route.

    Clears user session and redirects to login page.
    """
    # Log logout event before clearing session
    security_logger.info(
        f"User logout: user_id={current_user.id}, email={current_user.email}, "
        f"role={current_user.role}, ip={request.remote_addr}, "
        f"timestamp={datetime.now(timezone.utc).isoformat()}"
    )

    logout_user()
    flash('Uspešno ste se odjavili.', 'success')
    return redirect(url_for('auth.login'))
