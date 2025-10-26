"""Artikli Blueprint for Product/Service CRUD operations."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.artikal import Artikal
from app.forms.artikal import ArtikalCreateForm, ArtikalEditForm
from app.utils.query_helpers import filter_by_firma, get_user_firma_id
from datetime import datetime, timezone
from sqlalchemy import asc, desc, or_
import logging

security_logger = logging.getLogger('security')

artikli_bp = Blueprint('artikli', __name__, url_prefix='/artikli')


@artikli_bp.route('/')
@login_required
def lista():
    """
    List all artikli with tenant isolation, sorting, search, and pagination.

    Query Parameters:
        sort_by (str): Column to sort by (naziv_asc, naziv_desc, created_at_asc, created_at_desc). Default: naziv_asc
        search (str): Search term for naziv
        page (int): Page number for pagination. Default: 1

    Returns:
        Rendered template with paginated list of artikli (tenant isolated)
    """
    # Get query parameters
    sort_by = request.args.get('sort_by', 'naziv_asc')
    search_term = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)

    # Parse sort_by into column and direction
    sort_mapping = {
        'naziv_asc': (Artikal.naziv, asc),
        'naziv_desc': (Artikal.naziv, desc),
        'created_at_asc': (Artikal.created_at, asc),
        'created_at_desc': (Artikal.created_at, desc)
    }

    if sort_by not in sort_mapping:
        sort_by = 'naziv_asc'  # Fallback to default

    sort_column, order_func = sort_mapping[sort_by]

    # Build query with tenant isolation
    query = filter_by_firma(Artikal.query)

    # Apply search filter (naziv only)
    if search_term:
        query = query.filter(Artikal.naziv.ilike(f'%{search_term}%'))

    # Apply sorting
    query = query.order_by(order_func(sort_column))

    # Apply pagination (20 items per page)
    pagination = query.paginate(page=page, per_page=20, error_out=False)

    return render_template(
        'artikli/lista.html',
        artikli=pagination.items,
        pagination=pagination,
        sort_by=sort_by,
        search_term=search_term
    )


@artikli_bp.route('/novi', methods=['GET', 'POST'])
@login_required
def novi():
    """
    Create new artikal.

    Returns:
        GET: Rendered form template
        POST: Redirect to artikal detail on success, form with errors on failure
    """
    form = ArtikalCreateForm()

    if form.validate_on_submit():
        try:
            # Get firma_id (tenant isolation)
            # For pausalac: uses their firma_id
            # For admin: uses selected firma from session (admin_selected_firma_id)
            firma_id = get_user_firma_id()

            if not firma_id:
                flash('Greška: Admin mora prvo selektovati firmu (koristi dropdown u navigation bar-u).', 'danger')
                return render_template('artikli/novi.html', form=form)

            # Create new artikal
            artikal = Artikal(
                firma_id=firma_id,
                naziv=form.naziv.data,
                opis=form.opis.data or None,
                podrazumevana_cena=form.podrazumevana_cena.data,
                jedinica_mere=form.jedinica_mere.data
            )

            db.session.add(artikal)
            db.session.commit()

            # Security logging
            security_logger.info(
                f"Artikal created: artikal_id={artikal.id}, naziv={artikal.naziv}, "
                f"firma_id={artikal.firma_id}, created_by={current_user.email}, "
                f"ip={request.remote_addr}, timestamp={datetime.now(timezone.utc).isoformat()}"
            )

            flash(f'Artikal "{artikal.naziv}" je uspešno kreiran!', 'success')
            return redirect(url_for('artikli.detail', id=artikal.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Greška pri kreiranju artikla: {str(e)}', 'danger')
            return render_template('artikli/novi.html', form=form)

    return render_template('artikli/novi.html', form=form)


@artikli_bp.route('/<int:id>')
@login_required
def detail(id):
    """
    View artikal details with tenant isolation.

    Args:
        id: Artikal ID

    Returns:
        Rendered template with artikal details
        404 if artikal doesn't exist or doesn't belong to user's firma
    """
    artikal = filter_by_firma(Artikal.query).filter_by(id=id).first_or_404()
    return render_template('artikli/detail.html', artikal=artikal)


@artikli_bp.route('/<int:id>/izmeni', methods=['GET', 'POST'])
@login_required
def izmeni(id):
    """
    Edit existing artikal with tenant isolation.

    Args:
        id: Artikal ID

    Returns:
        GET: Rendered form template with prepopulated data
        POST: Redirect to artikal detail on success, form with errors on failure
        404 if artikal doesn't exist or doesn't belong to user's firma
    """
    artikal = filter_by_firma(Artikal.query).filter_by(id=id).first_or_404()
    form = ArtikalEditForm()

    if form.validate_on_submit():
        try:
            # Update artikal with new data
            artikal.naziv = form.naziv.data
            artikal.opis = form.opis.data or None
            artikal.podrazumevana_cena = form.podrazumevana_cena.data
            artikal.jedinica_mere = form.jedinica_mere.data

            db.session.commit()

            # Security logging
            security_logger.info(
                f"Artikal updated: artikal_id={artikal.id}, naziv={artikal.naziv}, "
                f"firma_id={artikal.firma_id}, updated_by={current_user.email}, "
                f"ip={request.remote_addr}, timestamp={datetime.now(timezone.utc).isoformat()}"
            )

            flash(f'Artikal "{artikal.naziv}" je uspešno izmenjen!', 'success')
            return redirect(url_for('artikli.detail', id=artikal.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Greška pri izmeni artikla: {str(e)}', 'danger')
            return render_template('artikli/izmeni.html', form=form, artikal=artikal)

    # Prepopulate form with existing data on GET request
    if request.method == 'GET':
        form.naziv.data = artikal.naziv
        form.opis.data = artikal.opis
        form.podrazumevana_cena.data = artikal.podrazumevana_cena
        form.jedinica_mere.data = artikal.jedinica_mere

    return render_template('artikli/izmeni.html', form=form, artikal=artikal)


@artikli_bp.route('/<int:id>/obrisi', methods=['POST'])
@login_required
def obrisi(id):
    """
    Delete artikal with tenant isolation.

    Note: Artikli can be safely deleted because their data is copied to faktura_stavke,
    not referenced. Deleting an artikal does not affect existing fakture.

    Args:
        id: Artikal ID

    Returns:
        Redirect to artikli list on success or failure
        404 if artikal doesn't exist or doesn't belong to user's firma
    """
    artikal = filter_by_firma(Artikal.query).filter_by(id=id).first_or_404()
    artikal_naziv = artikal.naziv

    try:
        # Delete artikal (safe to delete - data is copied to faktura_stavke, not referenced)
        db.session.delete(artikal)
        db.session.commit()

        # Security logging
        security_logger.info(
            f"Artikal deleted: artikal_id={id}, naziv={artikal_naziv}, "
            f"firma_id={artikal.firma_id}, deleted_by={current_user.email}, "
            f"ip={request.remote_addr}, timestamp={datetime.now(timezone.utc).isoformat()}"
        )

        flash(f'Artikal "{artikal_naziv}" je uspešno obrisan.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Greška pri brisanju artikla: {str(e)}', 'danger')

    return redirect(url_for('artikli.lista'))
