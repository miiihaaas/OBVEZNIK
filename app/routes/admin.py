"""Admin Blueprint for User Management and PausalnFirma CRUD operations."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.forms.user import UserCreateForm, UserEditForm
from app.forms.pausaln_firma import PausalnFirmaCreateForm, PausalnFirmaEditForm
from app.utils.decorators import admin_required
from app.services import nbs_komitent_service
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy import asc, desc, func, or_
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
    List all paušalne firme with sorting, search, and pagination (Admin only).

    Query Parameters:
        sort (str): Column to sort by (naziv, pib, created_at). Default: naziv
        order (str): Sort order (asc, desc). Default: asc
        search (str): Search term for naziv or PIB
        page (int): Page number for pagination. Default: 1

    Returns:
        Rendered template with paginated list of paušalne firme
    """
    # Get query parameters
    sort_by = request.args.get('sort', 'naziv')
    order_dir = request.args.get('order', 'asc')
    search_term = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)

    # Validate sort column (security: prevent SQL injection)
    allowed_sort_columns = {
        'naziv': PausalnFirma.naziv,
        'pib': PausalnFirma.pib,
        'created_at': PausalnFirma.created_at
    }

    if sort_by not in allowed_sort_columns:
        sort_by = 'naziv'  # Fallback to default

    sort_column = allowed_sort_columns[sort_by]

    # Build query
    query = PausalnFirma.query

    # Apply search filter
    if search_term:
        query = query.filter(
            or_(
                PausalnFirma.naziv.ilike(f'%{search_term}%'),
                PausalnFirma.pib.ilike(f'%{search_term}%')
            )
        )

    # Apply sorting
    order_func = desc if order_dir == 'desc' else asc
    query = query.order_by(order_func(sort_column))

    # Apply pagination
    pagination = query.paginate(page=page, per_page=20, error_out=False)

    return render_template(
        'admin/firme.html',
        firme=pagination.items,
        pagination=pagination,
        sort_by=sort_by,
        order_dir=order_dir,
        search_term=search_term
    )


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


@admin_bp.route('/firme/<int:firma_id>/izmeni', methods=['GET', 'POST'])
@login_required
@admin_required
def firma_edit(firma_id):
    """
    Edit existing paušalna firma (Admin only).

    Args:
        firma_id: PausalnFirma ID

    Returns:
        GET: Rendered form template with prepopulated data
        POST: Redirect to firma detail on success, form with errors on failure
    """
    firma = db.session.get(PausalnFirma, firma_id) or abort(404)
    form = PausalnFirmaEditForm()

    if form.validate_on_submit():
        # CRITICAL: PIB is immutable - cannot be changed after firma creation (SEC-001)
        if form.pib.data != firma.pib:
            flash('PIB ne može biti izmenjen nakon kreiranja firme.', 'danger')
            return render_template('admin/pausaln_firma_edit.html', form=form, firma=firma)

        try:
            # Parse dinarski računi from JSON hidden field
            dinarski_racuni = json.loads(form.dinarski_racuni_json.data) if form.dinarski_racuni_json.data else []

            # Parse devizni računi from JSON hidden field
            devizni_racuni = json.loads(form.devizni_racuni_json.data) if form.devizni_racuni_json.data else []

            # Update firma with new data (PIB remains unchanged)
            firma.naziv = form.naziv.data
            firma.maticni_broj = form.maticni_broj.data
            firma.adresa = form.adresa.data
            firma.broj = form.broj.data
            firma.postanski_broj = form.postanski_broj.data
            firma.mesto = form.mesto.data
            firma.drzava = form.drzava.data
            firma.telefon = form.telefon.data
            firma.email = form.email.data or ''
            firma.dinarski_racuni = dinarski_racuni
            firma.devizni_racuni = devizni_racuni if devizni_racuni else None
            firma.prefiks_fakture = form.prefiks_fakture.data or None
            firma.sufiks_fakture = form.sufiks_fakture.data or None
            firma.pdv_kategorija = form.pdv_kategorija.data or 'SS'
            firma.sifra_osnova = form.sifra_osnova.data or 'PDV-RS-33'

            db.session.commit()

            # Security logging
            security_logger.info(
                f"PausalnFirma updated: firma_id={firma.id}, naziv={firma.naziv}, pib={firma.pib}, "
                f"updated_by={current_user.email}, ip={request.remote_addr}, "
                f"timestamp={datetime.now(timezone.utc).isoformat()}"
            )

            flash(f'Paušalna firma "{firma.naziv}" je uspešno izmenjena!', 'success')
            return redirect(url_for('admin.firma_detail', firma_id=firma.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Greška pri izmeni firme: {str(e)}', 'danger')
            return render_template('admin/pausaln_firma_edit.html', form=form, firma=firma)

    # Prepopulate form with existing data on GET request
    if request.method == 'GET':
        form.pib.data = firma.pib
        form.naziv.data = firma.naziv
        form.maticni_broj.data = firma.maticni_broj
        form.adresa.data = firma.adresa
        form.broj.data = firma.broj
        form.postanski_broj.data = firma.postanski_broj
        form.mesto.data = firma.mesto
        form.drzava.data = firma.drzava
        form.telefon.data = firma.telefon
        form.email.data = firma.email
        form.dinarski_racuni_json.data = json.dumps(firma.dinarski_racuni or [])
        form.devizni_racuni_json.data = json.dumps(firma.devizni_racuni or [])
        form.prefiks_fakture.data = firma.prefiks_fakture
        form.sufiks_fakture.data = firma.sufiks_fakture
        form.pdv_kategorija.data = firma.pdv_kategorija
        form.sifra_osnova.data = firma.sifra_osnova

    return render_template('admin/pausaln_firma_edit.html', form=form, firma=firma)


@admin_bp.route('/firme/<int:firma_id>/obrisi', methods=['POST'])
@login_required
@admin_required
def firma_delete(firma_id):
    """
    Delete paušalna firma with CASCADE delete (Admin only).

    Args:
        firma_id: PausalnFirma ID

    Returns:
        Redirect to firme list on success or failure
    """
    firma = db.session.get(PausalnFirma, firma_id) or abort(404)
    firma_naziv = firma.naziv

    try:
        # Delete firma (CASCADE will automatically delete related records)
        db.session.delete(firma)
        db.session.commit()

        # Security logging
        security_logger.info(
            f"PausalnFirma deleted: firma_id={firma_id}, naziv={firma_naziv}, "
            f"deleted_by={current_user.email}, ip={request.remote_addr}, "
            f"timestamp={datetime.now(timezone.utc).isoformat()}"
        )

        flash(f'Paušalna firma "{firma_naziv}" je uspešno obrisana.', 'success')

    except IntegrityError as e:
        db.session.rollback()
        flash(f'Greška pri brisanju firme: {str(e)}', 'danger')

    except Exception as e:
        db.session.rollback()
        flash(f'Greška pri brisanju firme: {str(e)}', 'danger')

    return redirect(url_for('admin.firme'))
