"""Admin Blueprint for User Management and PausalnFirma CRUD operations."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.forms.user import UserCreateForm, UserEditForm
from app.forms.pausaln_firma import PausalnFirmaCreateForm
from app.utils.decorators import admin_required
from app.services import nbs_komitent_service
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
import logging
import json

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
    user = db.session.get(User, id) or abort(404)
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
        if form.password.data and form.password.data.strip():
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
    user = db.session.get(User, id) or abort(404)

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


# ===== PausalnFirma CRUD Routes =====

@admin_bp.route('/firme')
@login_required
@admin_required
def firme():
    """
    List all paušalne firme (Admin only).

    Returns:
        Rendered template with list of all paušalne firme
    """
    firme = PausalnFirma.query.order_by(PausalnFirma.naziv).all()
    return render_template('admin/firme.html', firme=firme)


@admin_bp.route('/firme/nova', methods=['GET', 'POST'])
@login_required
@admin_required
def firma_create():
    """
    Create new paušalna firma (Admin only).

    Returns:
        GET: Rendered form template
        POST: Redirect to firma detail on success, form with errors on failure
    """
    form = PausalnFirmaCreateForm()

    if form.validate_on_submit():
        try:
            # Parse dinarski računi from JSON hidden field
            dinarski_racuni = json.loads(form.dinarski_racuni_json.data) if form.dinarski_racuni_json.data else []

            # Parse devizni računi from JSON hidden field
            devizni_racuni = json.loads(form.devizni_racuni_json.data) if form.devizni_racuni_json.data else []

            # Create new PausalnFirma
            firma = PausalnFirma(
                pib=form.pib.data,
                maticni_broj=form.maticni_broj.data,
                naziv=form.naziv.data,
                adresa=form.adresa.data,
                broj=form.broj.data,
                postanski_broj=form.postanski_broj.data,
                mesto=form.mesto.data,
                drzava=form.drzava.data,
                telefon=form.telefon.data,
                email=form.email.data or '',
                dinarski_racuni=dinarski_racuni,
                devizni_racuni=devizni_racuni if devizni_racuni else None,
                prefiks_fakture=form.prefiks_fakture.data or None,
                sufiks_fakture=form.sufiks_fakture.data or None,
                pdv_kategorija=form.pdv_kategorija.data or 'SS',
                sifra_osnova=form.sifra_osnova.data or 'PDV-RS-33'
            )

            db.session.add(firma)
            db.session.commit()

            # Security logging
            security_logger.info(
                f"PausalnFirma created: firma_id={firma.id}, naziv={firma.naziv}, pib={firma.pib}, "
                f"created_by={current_user.email}, ip={request.remote_addr}, "
                f"timestamp={datetime.now(timezone.utc).isoformat()}"
            )

            flash(f'Paušalna firma "{firma.naziv}" je uspešno kreirana!', 'success')
            return redirect(url_for('admin.firma_detail', firma_id=firma.id))

        except IntegrityError:
            db.session.rollback()
            flash('Greška: Firma sa ovim PIB-om već postoji.', 'danger')
            return render_template('admin/pausaln_firma_create.html', form=form)
        except Exception as e:
            db.session.rollback()
            flash(f'Greška pri kreiranju firme: {str(e)}', 'danger')
            return render_template('admin/pausaln_firma_create.html', form=form)

    return render_template('admin/pausaln_firma_create.html', form=form)


@admin_bp.route('/firme/<int:firma_id>')
@login_required
@admin_required
def firma_detail(firma_id):
    """
    View paušalna firma details (Admin only).

    Args:
        firma_id: PausalnFirma ID

    Returns:
        Rendered template with firma details
    """
    firma = db.session.get(PausalnFirma, firma_id) or abort(404)
    return render_template('admin/pausaln_firma_detail.html', firma=firma)
