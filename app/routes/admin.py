"""Admin Blueprint for User Management (CRUD operations)."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.forms.user import UserCreateForm, UserEditForm
from app.utils.decorators import admin_required
from datetime import datetime, timezone
import logging

security_logger = logging.getLogger('security')

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """
    List all users (Admin only).

    Returns:
        Rendered template with list of all users
    """
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/novi', methods=['GET', 'POST'])
@login_required
@admin_required
def user_create():
    """
    Create new user (Admin only).

    Returns:
        GET: Rendered form template
        POST: Redirect to users list on success, form with errors on failure
    """
    form = UserCreateForm()

    # Populate firma_id choices dynamically
    form.firma_id.choices = [(0, 'Izaberite firmu...')] + [
        (f.id, f.naziv) for f in PausalnFirma.query.order_by(PausalnFirma.naziv).all()
    ]

    if form.validate_on_submit():
        # Create new user
        user = User(
            email=form.email.data,
            full_name=form.full_name.data,
            role=form.role.data,
            firma_id=form.firma_id.data if form.firma_id.data and form.firma_id.data != 0 else None
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        # Security logging
        security_logger.info(
            f"User created: user_id={user.id}, email={user.email}, role={user.role}, "
            f"created_by={current_user.email}, ip={request.remote_addr}, "
            f"timestamp={datetime.now(timezone.utc).isoformat()}"
        )

        flash(f'Korisnik {user.email} je uspešno kreiran.', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', form=form, action='Kreiraj')


@admin_bp.route('/users/<int:id>/izmeni', methods=['GET', 'POST'])
@login_required
@admin_required
def user_edit(id):
    """
    Edit existing user (Admin only).

    Args:
        id: User ID to edit

    Returns:
        GET: Rendered form template with current user data
        POST: Redirect to users list on success, form with errors on failure
    """
    user = User.query.get_or_404(id)
    form = UserEditForm(original_email=user.email, obj=user)

    # Populate firma_id choices dynamically
    form.firma_id.choices = [(0, 'Izaberite firmu...')] + [
        (f.id, f.naziv) for f in PausalnFirma.query.order_by(PausalnFirma.naziv).all()
    ]

    if request.method == 'GET':
        # Pre-populate form fields
        form.full_name.data = user.full_name
        form.email.data = user.email
        form.role.data = user.role
        form.firma_id.data = user.firma_id if user.firma_id else 0

    if form.validate_on_submit():
        # Update user fields
        user.full_name = form.full_name.data
        user.email = form.email.data
        user.role = form.role.data
        user.firma_id = form.firma_id.data if form.firma_id.data and form.firma_id.data != 0 else None

        # Update password only if new password is provided
        if form.password.data:
            user.set_password(form.password.data)

        db.session.commit()

        # Security logging
        security_logger.info(
            f"User updated: user_id={user.id}, email={user.email}, role={user.role}, "
            f"updated_by={current_user.email}, ip={request.remote_addr}, "
            f"timestamp={datetime.now(timezone.utc).isoformat()}"
        )

        flash(f'Korisnik {user.email} je uspešno ažuriran.', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', form=form, action='Izmeni', user=user)


@admin_bp.route('/users/<int:id>/obrisi', methods=['POST'])
@login_required
@admin_required
def user_delete(id):
    """
    Delete user (Admin only).

    Args:
        id: User ID to delete

    Returns:
        Redirect to users list with success/error message
    """
    user = User.query.get_or_404(id)

    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        flash('Ne možete obrisati svoj nalog.', 'danger')
        return redirect(url_for('admin.users'))

    # Store email for logging before deletion
    email = user.email
    role = user.role
    user_id = user.id

    db.session.delete(user)
    db.session.commit()

    # Security logging
    security_logger.info(
        f"User deleted: user_id={user_id}, email={email}, role={role}, "
        f"deleted_by={current_user.email}, ip={request.remote_addr}, "
        f"timestamp={datetime.now(timezone.utc).isoformat()}"
    )

    flash(f'Korisnik {email} je uspešno obrisan.', 'success')
    return redirect(url_for('admin.users'))
