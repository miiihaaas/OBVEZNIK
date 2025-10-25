"""Komitenti Blueprint for Client CRUD operations."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.komitent import Komitent
from app.forms.komitent import KomitentCreateForm, KomitentEditForm
from app.utils.query_helpers import filter_by_firma
from app.services import nbs_komitent_service
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy import asc, desc, or_
import logging

security_logger = logging.getLogger('security')

komitenti_bp = Blueprint('komitenti', __name__, url_prefix='/komitenti')


@komitenti_bp.route('/')
@login_required
def lista():
    """
    List all komitenti with tenant isolation, sorting, search, and pagination.

    Query Parameters:
        sort (str): Column to sort by (naziv, pib, created_at). Default: naziv
        order (str): Sort order (asc, desc). Default: asc
        search (str): Search term for naziv or PIB
        page (int): Page number for pagination. Default: 1

    Returns:
        Rendered template with paginated list of komitenti (tenant isolated)
    """
    # Get query parameters
    sort_by = request.args.get('sort', 'naziv')
    order_dir = request.args.get('order', 'asc')
    search_term = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)

    # Validate sort column (security: prevent SQL injection)
    allowed_sort_columns = {
        'naziv': Komitent.naziv,
        'pib': Komitent.pib,
        'created_at': Komitent.created_at
    }

    if sort_by not in allowed_sort_columns:
        sort_by = 'naziv'  # Fallback to default

    sort_column = allowed_sort_columns[sort_by]

    # Build query with tenant isolation
    query = filter_by_firma(Komitent.query)

    # Apply search filter
    if search_term:
        query = query.filter(
            or_(
                Komitent.naziv.ilike(f'%{search_term}%'),
                Komitent.pib.ilike(f'%{search_term}%')
            )
        )

    # Apply sorting
    order_func = desc if order_dir == 'desc' else asc
    query = query.order_by(order_func(sort_column))

    # Apply pagination
    pagination = query.paginate(page=page, per_page=20, error_out=False)

    return render_template(
        'komitenti/lista.html',
        komitenti=pagination.items,
        pagination=pagination,
        sort_by=sort_by,
        order_dir=order_dir,
        search_term=search_term
    )


@komitenti_bp.route('/novi', methods=['GET', 'POST'])
@login_required
def novi():
    """
    Create new komitent.

    Returns:
        GET: Rendered form template
        POST: Redirect to komitent detail on success, form with errors on failure
    """
    form = KomitentCreateForm()

    if form.validate_on_submit():
        try:
            # Get firma_id (tenant isolation)
            firma_id = current_user.firma_id if not current_user.is_admin() else None

            if not firma_id:
                flash('Greška: Korisnik nije povezan sa paušalnom firmom.', 'danger')
                return render_template('komitenti/novi.html', form=form)

            # Create new Komitent
            komitent = Komitent(
                firma_id=firma_id,
                pib=form.pib.data,
                maticni_broj=form.maticni_broj.data,
                naziv=form.naziv.data,
                adresa=form.adresa.data,
                broj=form.broj.data,
                postanski_broj=form.postanski_broj.data,
                mesto=form.mesto.data,
                drzava=form.drzava.data,
                email=form.email.data,
                kontakt_osoba=form.kontakt_osoba.data or None,
                napomene=form.napomene.data or None
            )

            db.session.add(komitent)
            db.session.commit()

            # Security logging
            security_logger.info(
                f"Komitent created: komitent_id={komitent.id}, naziv={komitent.naziv}, pib={komitent.pib}, "
                f"firma_id={komitent.firma_id}, created_by={current_user.email}, ip={request.remote_addr}, "
                f"timestamp={datetime.now(timezone.utc).isoformat()}"
            )

            flash(f'Komitent "{komitent.naziv}" je uspešno kreiran!', 'success')
            return redirect(url_for('komitenti.detail', id=komitent.id))

        except IntegrityError:
            db.session.rollback()
            flash('Greška: Komitent sa ovim PIB-om već postoji u vašoj firmi.', 'danger')
            return render_template('komitenti/novi.html', form=form)
        except Exception as e:
            db.session.rollback()
            flash(f'Greška pri kreiranju komitenta: {str(e)}', 'danger')
            return render_template('komitenti/novi.html', form=form)

    return render_template('komitenti/novi.html', form=form)


@komitenti_bp.route('/<int:id>')
@login_required
def detail(id):
    """
    View komitent details with tenant isolation.

    Args:
        id: Komitent ID

    Returns:
        Rendered template with komitent details
        404 if komitent doesn't exist or doesn't belong to user's firma
    """
    komitent = filter_by_firma(Komitent.query).filter_by(id=id).first_or_404()
    return render_template('komitenti/detail.html', komitent=komitent)


@komitenti_bp.route('/<int:id>/izmeni', methods=['GET', 'POST'])
@login_required
def izmeni(id):
    """
    Edit existing komitent with tenant isolation.

    Args:
        id: Komitent ID

    Returns:
        GET: Rendered form template with prepopulated data
        POST: Redirect to komitent detail on success, form with errors on failure
        404 if komitent doesn't exist or doesn't belong to user's firma
    """
    komitent = filter_by_firma(Komitent.query).filter_by(id=id).first_or_404()
    form = KomitentEditForm()

    if form.validate_on_submit():
        # CRITICAL: PIB is immutable - cannot be changed after komitent creation
        if form.pib.data != komitent.pib:
            flash('PIB ne može biti izmenjen nakon kreiranja komitenta.', 'danger')
            return render_template('komitenti/izmeni.html', form=form, komitent=komitent)

        try:
            # Update komitent with new data (PIB remains unchanged)
            komitent.naziv = form.naziv.data
            komitent.maticni_broj = form.maticni_broj.data
            komitent.adresa = form.adresa.data
            komitent.broj = form.broj.data
            komitent.postanski_broj = form.postanski_broj.data
            komitent.mesto = form.mesto.data
            komitent.drzava = form.drzava.data
            komitent.email = form.email.data
            komitent.kontakt_osoba = form.kontakt_osoba.data or None
            komitent.napomene = form.napomene.data or None

            db.session.commit()

            # Security logging
            security_logger.info(
                f"Komitent updated: komitent_id={komitent.id}, naziv={komitent.naziv}, pib={komitent.pib}, "
                f"updated_by={current_user.email}, ip={request.remote_addr}, "
                f"timestamp={datetime.now(timezone.utc).isoformat()}"
            )

            flash(f'Komitent "{komitent.naziv}" je uspešno izmenjen!', 'success')
            return redirect(url_for('komitenti.detail', id=komitent.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Greška pri izmeni komitenta: {str(e)}', 'danger')
            return render_template('komitenti/izmeni.html', form=form, komitent=komitent)

    # Prepopulate form with existing data on GET request
    if request.method == 'GET':
        form.pib.data = komitent.pib
        form.naziv.data = komitent.naziv
        form.maticni_broj.data = komitent.maticni_broj
        form.adresa.data = komitent.adresa
        form.broj.data = komitent.broj
        form.postanski_broj.data = komitent.postanski_broj
        form.mesto.data = komitent.mesto
        form.drzava.data = komitent.drzava
        form.email.data = komitent.email
        form.kontakt_osoba.data = komitent.kontakt_osoba
        form.napomene.data = komitent.napomene

    return render_template('komitenti/izmeni.html', form=form, komitent=komitent)


@komitenti_bp.route('/<int:id>/obrisi', methods=['POST'])
@login_required
def obrisi(id):
    """
    Delete komitent with tenant isolation and foreign key constraint check.

    Args:
        id: Komitent ID

    Returns:
        Redirect to komitenti list on success or failure
        404 if komitent doesn't exist or doesn't belong to user's firma
    """
    komitent = filter_by_firma(Komitent.query).filter_by(id=id).first_or_404()
    komitent_naziv = komitent.naziv
    komitent_pib = komitent.pib

    try:
        # Check if komitent has fakture (RESTRICT constraint)
        if komitent.fakture and len(komitent.fakture) > 0:
            flash(
                f'Ne možete obrisati komitenta "{komitent_naziv}" jer postoje fakture vezane za njega. '
                f'Prvo stornirajte sve fakture.',
                'danger'
            )
            return redirect(url_for('komitenti.detail', id=id))

        # Delete komitent
        db.session.delete(komitent)
        db.session.commit()

        # Security logging
        security_logger.info(
            f"Komitent deleted: komitent_id={id}, naziv={komitent_naziv}, pib={komitent_pib}, "
            f"deleted_by={current_user.email}, ip={request.remote_addr}, "
            f"timestamp={datetime.now(timezone.utc).isoformat()}"
        )

        flash(f'Komitent "{komitent_naziv}" je uspešno obrisan.', 'success')

    except IntegrityError as e:
        db.session.rollback()
        flash(
            f'Ne možete obrisati komitenta "{komitent_naziv}" jer postoje fakture vezane za njega.',
            'danger'
        )

    except Exception as e:
        db.session.rollback()
        flash(f'Greška pri brisanju komitenta: {str(e)}', 'danger')

    return redirect(url_for('komitenti.lista'))


@komitenti_bp.route('/api/nbs/firma/<pib>')
@login_required
def nbs_firma_lookup(pib):
    """
    AJAX endpoint for NBS API company lookup by PIB.

    Args:
        pib: PIB (8 or 9 digits)

    Returns:
        JSON response with company data or error message
        Example success: {'success': True, 'data': {...}}
        Example error: {'success': False, 'message': 'PIB nije pronađen'}
    """
    firma_data = nbs_komitent_service.fetch_company_by_pib(pib)

    if firma_data:
        return jsonify({'success': True, 'data': firma_data})
    else:
        return jsonify({'success': False, 'message': 'PIB nije pronađen u NBS bazi'})
