"""Memorandumi Blueprint for internal documentation CRUD operations."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.memorandum import Memorandum
from app.models.komitent import Komitent
from app.models.faktura import Faktura
from app.forms.memorandum import MemorandumCreateForm, MemorandumEditForm
from app.utils.query_helpers import filter_by_firma, get_user_firma_id
from datetime import datetime, timezone
from sqlalchemy import asc, desc
import logging

security_logger = logging.getLogger('security')

memorandumi_bp = Blueprint('memorandumi', __name__, url_prefix='/memorandumi')


@memorandumi_bp.route('/')
@login_required
def lista():
    """
    List all memorandumi with tenant isolation, sorting, search, filtering, and pagination.

    Query Parameters:
        search (str): Search term for naslov
        datum_od (str): Filter by date from (YYYY-MM-DD)
        datum_do (str): Filter by date to (YYYY-MM-DD)
        komitent_id (int): Filter by komitent ID
        page (int): Page number for pagination. Default: 1

    Returns:
        Rendered template with paginated list of memorandumi (tenant isolated)
    """
    # Get query parameters
    search_term = request.args.get('search', '').strip()
    datum_od = request.args.get('datum_od', '').strip()
    datum_do = request.args.get('datum_do', '').strip()
    komitent_id = request.args.get('komitent_id', type=int)
    page = request.args.get('page', 1, type=int)

    # Build query with tenant isolation
    query = filter_by_firma(Memorandum.query)

    # Apply search filter (naslov only)
    if search_term:
        query = query.filter(Memorandum.naslov.ilike(f'%{search_term}%'))

    # Apply date filters
    if datum_od:
        try:
            from datetime import datetime
            datum_od_obj = datetime.strptime(datum_od, '%Y-%m-%d').date()
            query = query.filter(Memorandum.datum >= datum_od_obj)
        except ValueError:
            flash('Nevažeći format datuma "od".', 'warning')

    if datum_do:
        try:
            from datetime import datetime
            datum_do_obj = datetime.strptime(datum_do, '%Y-%m-%d').date()
            query = query.filter(Memorandum.datum <= datum_do_obj)
        except ValueError:
            flash('Nevažeći format datuma "do".', 'warning')

    # Apply komitent filter
    if komitent_id:
        query = query.filter(Memorandum.komitent_id == komitent_id)

    # Apply sorting (default: most recent first)
    query = query.order_by(desc(Memorandum.datum), desc(Memorandum.created_at))

    # Apply pagination (20 items per page)
    pagination = query.paginate(page=page, per_page=20, error_out=False)

    # Get komitenti for filter dropdown (tenant isolated)
    firma_id = get_user_firma_id()
    komitenti = []
    if firma_id:
        komitenti = filter_by_firma(Komitent.query).order_by(Komitent.naziv).all()

    return render_template(
        'memorandumi/lista.html',
        memorandumi=pagination.items,
        pagination=pagination,
        search_term=search_term,
        datum_od=datum_od,
        datum_do=datum_do,
        komitent_id=komitent_id,
        komitenti=komitenti
    )


@memorandumi_bp.route('/novi', methods=['GET', 'POST'])
@login_required
def novi():
    """
    Create new memorandum.

    Returns:
        GET: Rendered form template
        POST: Redirect to memorandum detail on success, form with errors on failure
    """
    form = MemorandumCreateForm()

    # Populate choices for SelectFields (tenant isolated)
    firma_id = get_user_firma_id()
    if firma_id:
        # Komitenti choices
        komitenti = filter_by_firma(Komitent.query).order_by(Komitent.naziv).all()
        form.komitent_id.choices = [('', '-- Bez komitenta --')] + [(k.id, k.naziv) for k in komitenti]

        # Fakture choices (samo aktivne fakture)
        fakture = filter_by_firma(Faktura.query).filter(
            Faktura.status.in_(['draft', 'poslata', 'placena'])
        ).order_by(desc(Faktura.datum_prometa)).limit(50).all()
        form.faktura_id.choices = [('', '-- Bez fakture --')] + [(f.id, f'{f.broj_fakture} - {f.komitent.naziv}') for f in fakture]

    if form.validate_on_submit():
        try:
            # Get firma_id (tenant isolation)
            if not firma_id:
                flash('Greška: Admin mora prvo selektovati firmu (koristi dropdown u navigation bar-u).', 'danger')
                return render_template('memorandumi/novi.html', form=form)

            # Create new memorandum
            memorandum = Memorandum(
                firma_id=firma_id,
                naslov=form.naslov.data,
                sadrzaj=form.sadrzaj.data,
                datum=form.datum.data,
                komitent_id=form.komitent_id.data if form.komitent_id.data else None,
                faktura_id=form.faktura_id.data if form.faktura_id.data else None
            )

            db.session.add(memorandum)
            db.session.commit()

            # Security logging
            security_logger.info(
                f"Memorandum created: memo_id={memorandum.id}, naslov={memorandum.naslov}, "
                f"firma_id={memorandum.firma_id}, created_by={current_user.email}, "
                f"ip={request.remote_addr}, timestamp={datetime.now(timezone.utc).isoformat()}"
            )

            flash(f'Memorandum "{memorandum.naslov}" je uspešno kreiran!', 'success')
            return redirect(url_for('memorandumi.detail', id=memorandum.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Greška pri kreiranju memoranduma: {str(e)}', 'danger')
            return render_template('memorandumi/novi.html', form=form)

    return render_template('memorandumi/novi.html', form=form)


@memorandumi_bp.route('/<int:id>')
@login_required
def detail(id):
    """
    View memorandum details with tenant isolation.

    Args:
        id: Memorandum ID

    Returns:
        Rendered template with memorandum details
        404 if memorandum doesn't exist or doesn't belong to user's firma
    """
    memorandum = filter_by_firma(Memorandum.query).filter_by(id=id).first_or_404()
    return render_template('memorandumi/detail.html', memorandum=memorandum)


@memorandumi_bp.route('/<int:id>/izmeni', methods=['GET', 'POST'])
@login_required
def izmeni(id):
    """
    Edit existing memorandum with tenant isolation.

    Args:
        id: Memorandum ID

    Returns:
        GET: Rendered form template with prepopulated data
        POST: Redirect to memorandum detail on success, form with errors on failure
        404 if memorandum doesn't exist or doesn't belong to user's firma
    """
    memorandum = filter_by_firma(Memorandum.query).filter_by(id=id).first_or_404()
    form = MemorandumEditForm()

    # Populate choices for SelectFields (tenant isolated)
    firma_id = get_user_firma_id()
    if firma_id:
        # Komitenti choices
        komitenti = filter_by_firma(Komitent.query).order_by(Komitent.naziv).all()
        form.komitent_id.choices = [('', '-- Bez komitenta --')] + [(k.id, k.naziv) for k in komitenti]

        # Fakture choices
        fakture = filter_by_firma(Faktura.query).filter(
            Faktura.status.in_(['draft', 'poslata', 'placena'])
        ).order_by(desc(Faktura.datum_prometa)).limit(50).all()
        form.faktura_id.choices = [('', '-- Bez fakture --')] + [(f.id, f'{f.broj_fakture} - {f.komitent.naziv}') for f in fakture]

    if form.validate_on_submit():
        try:
            # Update memorandum with new data
            memorandum.naslov = form.naslov.data
            memorandum.sadrzaj = form.sadrzaj.data
            memorandum.datum = form.datum.data
            memorandum.komitent_id = form.komitent_id.data if form.komitent_id.data else None
            memorandum.faktura_id = form.faktura_id.data if form.faktura_id.data else None

            db.session.commit()

            # Security logging
            security_logger.info(
                f"Memorandum updated: memo_id={memorandum.id}, naslov={memorandum.naslov}, "
                f"firma_id={memorandum.firma_id}, updated_by={current_user.email}, "
                f"ip={request.remote_addr}, timestamp={datetime.now(timezone.utc).isoformat()}"
            )

            flash(f'Memorandum "{memorandum.naslov}" je uspešno izmenjen!', 'success')
            return redirect(url_for('memorandumi.detail', id=memorandum.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Greška pri izmeni memoranduma: {str(e)}', 'danger')
            return render_template('memorandumi/izmeni.html', form=form, memorandum=memorandum)

    # Prepopulate form with existing data on GET request
    if request.method == 'GET':
        form.naslov.data = memorandum.naslov
        form.sadrzaj.data = memorandum.sadrzaj
        form.datum.data = memorandum.datum
        form.komitent_id.data = memorandum.komitent_id
        form.faktura_id.data = memorandum.faktura_id

    return render_template('memorandumi/izmeni.html', form=form, memorandum=memorandum)


@memorandumi_bp.route('/<int:id>/obrisi', methods=['POST'])
@login_required
def obrisi(id):
    """
    Delete memorandum with tenant isolation.

    Args:
        id: Memorandum ID

    Returns:
        Redirect to memorandumi list
        404 if memorandum doesn't exist or doesn't belong to user's firma
    """
    memorandum = filter_by_firma(Memorandum.query).filter_by(id=id).first_or_404()

    try:
        naslov = memorandum.naslov
        memo_id = memorandum.id
        firma_id = memorandum.firma_id

        db.session.delete(memorandum)
        db.session.commit()

        # Security logging
        security_logger.info(
            f"Memorandum deleted: memo_id={memo_id}, naslov={naslov}, "
            f"firma_id={firma_id}, deleted_by={current_user.email}, "
            f"ip={request.remote_addr}, timestamp={datetime.now(timezone.utc).isoformat()}"
        )

        flash(f'Memorandum "{naslov}" je uspešno obrisan!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Greška pri brisanju memoranduma: {str(e)}', 'danger')

    return redirect(url_for('memorandumi.lista'))
