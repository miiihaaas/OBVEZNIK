"""Routes for Fakture (Invoices) management."""
import os
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_login import login_required, current_user
from app import db, limiter
from app.models.faktura import Faktura
from app.models.komitent import Komitent
from app.forms.faktura import FakturaCreateForm
from app.services.faktura_service import convert_profaktura_to_faktura, create_faktura, update_faktura, finalize_faktura, list_fakture, storniraj_fakturu
from app.utils.query_helpers import filter_by_firma

fakture_bp = Blueprint('fakture', __name__, url_prefix='/fakture')
logger = logging.getLogger(__name__)


@fakture_bp.route('/')
@login_required
@limiter.limit("100 per minute")  # Prevent DoS via complex filters
def lista():
    """
    Display list of all invoices for current user's firma with filters, search, sorting, and pagination.

    Query Parameters:
        - page: int - Page number (default: 1)
        - datum_od: date - Filter by start date (YYYY-MM-DD)
        - datum_do: date - Filter by end date (YYYY-MM-DD)
        - komitent_id: int - Filter by komitent
        - status: str - Filter by status ('draft', 'izdata', 'stornirana')
        - valuta: str - Filter by currency ('RSD', 'EUR', 'USD', 'GBP', 'CHF')
        - search: str - Search by invoice number
        - sort_by: str - Sort column ('broj_fakture', 'datum_prometa', 'ukupan_iznos_rsd')
        - sort_order: str - Sort order ('asc', 'desc')
        - firma_id: int - Admin-only: Filter by specific firma

    Returns:
        Rendered HTML template with paginated list of invoices
    """
    from datetime import datetime

    # Parse query parameters
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'datum_prometa')
    sort_order = request.args.get('sort_order', 'desc')

    # Build filters dictionary
    filters = {}

    # Date filters
    datum_od_str = request.args.get('datum_od')
    if datum_od_str:
        try:
            filters['datum_od'] = datetime.strptime(datum_od_str, '%Y-%m-%d').date()
        except ValueError as e:
            logger.warning(f"Invalid datum_od format: {datum_od_str}, user: {current_user.email}", exc_info=True)
            flash('Neispravan format datuma "od". Koristite YYYY-MM-DD format.', 'warning')

    datum_do_str = request.args.get('datum_do')
    if datum_do_str:
        try:
            filters['datum_do'] = datetime.strptime(datum_do_str, '%Y-%m-%d').date()
        except ValueError as e:
            logger.warning(f"Invalid datum_do format: {datum_do_str}, user: {current_user.email}", exc_info=True)
            flash('Neispravan format datuma "do". Koristite YYYY-MM-DD format.', 'warning')

    # Other filters
    if request.args.get('komitent_id'):
        filters['komitent_id'] = request.args.get('komitent_id', type=int)

    if request.args.get('status'):
        filters['status'] = request.args.get('status')

    if request.args.get('valuta'):
        filters['valuta'] = request.args.get('valuta')

    if request.args.get('tip_fakture'):
        filters['tip_fakture'] = request.args.get('tip_fakture')

    if request.args.get('search'):
        filters['search'] = request.args.get('search').strip()

    # Admin-only: firma filter
    if current_user.role == 'admin' and request.args.get('firma_id'):
        filters['firma_id'] = request.args.get('firma_id', type=int)

    # Call service layer to get paginated fakture
    pagination = list_fakture(
        user=current_user,
        filters=filters,
        page=page,
        per_page=20,
        sort_by=sort_by,
        sort_order=sort_order
    )

    # Get list of all pausaln firme for admin firma filter dropdown
    from app.models.pausaln_firma import PausalnFirma
    all_firme = []
    if current_user.role == 'admin':
        all_firme = PausalnFirma.query.filter_by(is_active=True).order_by(PausalnFirma.naziv).all()

    return render_template(
        'fakture/lista.html',
        pagination=pagination,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        all_firme=all_firme
    )


@fakture_bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova_faktura():
    """
    Create new invoice form.

    GET: Display form
    POST: Create draft invoice
    """
    form = FakturaCreateForm()

    # Story 4.4: Populate avansne fakture choices dynamically (for validation)
    avansne_fakture = filter_by_firma(Faktura.query).filter_by(
        tip_fakture='avansna',
        status='izdata'
    ).all()
    # NOTE: Use empty string '' instead of None to match HTML <option value="">

    form.avansna_faktura_id.choices = [('', 'Izaberite avansnu fakturu...')] + [
        (f.id, f'{f.broj_fakture} - {f.komitent.naziv if f.komitent else "N/A"}') for f in avansne_fakture
    ]

    if request.method == 'POST':
        current_app.logger.debug('POST request received for nova faktura')
        current_app.logger.debug(f'Form errors before validation: {form.errors}')

        if form.validate_on_submit():
            current_app.logger.info('Form validation passed for nova faktura')
            try:
                # Extract form data
                data = {
                    'tip_fakture': form.tip_fakture.data,
                    'valuta_fakture': form.valuta_fakture.data,  # For devizna fakture
                    'srednji_kurs': form.srednji_kurs.data,  # For devizna fakture
                    'ukupna_vrednost_posla': form.ukupna_vrednost_posla.data,  # For avansna fakture
                    'procenat_avansa': form.procenat_avansa.data,  # For avansna fakture
                    'opis_posla': form.opis_posla.data,  # For avansna fakture
                    'zatvara_avans': form.zatvara_avans.data,  # Story 4.4: Zatvaranje avansa
                    'avansna_faktura_id': form.avansna_faktura_id.data,  # Story 4.4: Zatvaranje avansa
                    'komitent_id': form.komitent_id.data,
                    'datum_prometa': form.datum_prometa.data,
                    'valuta_placanja': form.valuta_placanja.data,
                    'broj_ugovora': form.broj_ugovora.data,
                    'broj_odluke': form.broj_odluke.data,
                    'broj_narudzbenice': form.broj_narudzbenice.data,
                    'poziv_na_broj': form.poziv_na_broj.data,
                    'model': form.model.data,
                    'stavke': []
                }

                # Extract stavke data
                for stavka_form in form.stavke:
                    stavka_data = {
                        'artikal_id': stavka_form.artikal_id.data,
                        'naziv': stavka_form.naziv.data,
                        'kolicina': stavka_form.kolicina.data,
                        'jedinica_mere': stavka_form.jedinica_mere.data,
                        'cena': stavka_form.cena.data
                    }
                    data['stavke'].append(stavka_data)
                current_app.logger.info(f'Creating faktura with {len(data["stavke"])} stavke')
                # Create faktura using service
                faktura = create_faktura(data, current_user)

                # Success message with tip fakture (Story 4.3)
                tip_display = {
                    'standardna': 'Domaća faktura',
                    'profaktura': 'Profaktura',
                    'avansna': 'Avansna faktura',
                    'devizna': 'Devizna faktura'
                }.get(faktura.tip_fakture, 'Faktura')

                # Story 4.4: Enhanced message when closing avans
                if faktura.avansna_faktura_id:
                    avansna_faktura = Faktura.query.get(faktura.avansna_faktura_id)
                    avans_broj = avansna_faktura.broj_fakture if avansna_faktura else 'nepoznat'
                    flash(
                        f'{tip_display} {faktura.broj_fakture} uspešno kreirana u draft statusu '
                        f'sa zatvaranjem avansa {avans_broj}.',
                        'success'
                    )
                else:
                    flash(f'{tip_display} {faktura.broj_fakture} uspešno kreirana u draft statusu.', 'success')

                return redirect(url_for('fakture.detail', faktura_id=faktura.id))

            except Exception as e:
                db.session.rollback()
                flash(f'Greška pri kreiranju fakture: {str(e)}', 'danger')
                current_app.logger.error(f'Exception during faktura creation: {str(e)}', exc_info=True)
                # Return form with existing data so user can fix errors
        else:
            # Form validation failed
            current_app.logger.warning('Form validation FAILED for nova faktura')
            current_app.logger.warning(f'Form errors: {form.errors}')
            flash('Forma sadrži greške. Molimo proverite unete podatke.', 'danger')
            # Display specific errors
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'warning')

    # Load komitenti for dropdown (filtered by firma)
    komitenti = filter_by_firma(Komitent.query).all()

    return render_template('fakture/nova.html', form=form, komitenti=komitenti)


@fakture_bp.route('/<int:faktura_id>')
@login_required
def detail(faktura_id):
    """
    Display invoice detail view.

    Args:
        faktura_id: Invoice ID
    """
    # Get faktura with tenant isolation
    faktura = filter_by_firma(Faktura.query).filter_by(id=faktura_id).first_or_404()

    return render_template('fakture/detail.html', faktura=faktura)


@fakture_bp.route('/<int:faktura_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_faktura(faktura_id):
    """
    Edit existing draft invoice.

    GET: Display form prepopulated with existing data
    POST: Update draft invoice with new data

    Args:
        faktura_id: Invoice ID
    """
    # Get faktura with tenant isolation
    faktura = filter_by_firma(Faktura.query).filter_by(id=faktura_id).first_or_404()

    # Validation: Only draft invoices can be edited
    if faktura.status != 'draft':
        flash('Samo fakture u statusu "draft" mogu biti izmenjene. Ova faktura je već finalizovana.', 'danger')
        return redirect(url_for('fakture.detail', faktura_id=faktura_id))

    form = FakturaCreateForm()

    # Story 4.4: Populate avansne fakture choices dynamically (for validation)
    avansne_fakture = filter_by_firma(Faktura.query).filter_by(
        tip_fakture='avansna',
        status='izdata'
    ).all()
    # NOTE: Use empty string '' instead of None to match HTML <option value="">

    form.avansna_faktura_id.choices = [('', 'Izaberite avansnu fakturu...')] + [
        (f.id, f'{f.broj_fakture} - {f.komitent.naziv if f.komitent else "N/A"}') for f in avansne_fakture
    ]

    if request.method == 'POST':
        current_app.logger.debug('POST request received for edit faktura')
        current_app.logger.debug(f'Form errors before validation: {form.errors}')

        if form.validate_on_submit():
            current_app.logger.info('Form validation passed for edit faktura')
            try:
                # Extract form data
                data = {
                    'tip_fakture': form.tip_fakture.data,
                    'valuta_fakture': form.valuta_fakture.data,  # For devizna fakture
                    'srednji_kurs': form.srednji_kurs.data,  # For devizna fakture
                    'ukupna_vrednost_posla': form.ukupna_vrednost_posla.data,  # For avansna fakture
                    'procenat_avansa': form.procenat_avansa.data,  # For avansna fakture
                    'opis_posla': form.opis_posla.data,  # For avansna fakture
                    'zatvara_avans': form.zatvara_avans.data,  # Story 4.4: Zatvaranje avansa
                    'avansna_faktura_id': form.avansna_faktura_id.data,  # Story 4.4: Zatvaranje avansa
                    'komitent_id': form.komitent_id.data,
                    'datum_prometa': form.datum_prometa.data,
                    'valuta_placanja': form.valuta_placanja.data,
                    'broj_ugovora': form.broj_ugovora.data,
                    'broj_odluke': form.broj_odluke.data,
                    'broj_narudzbenice': form.broj_narudzbenice.data,
                    'poziv_na_broj': form.poziv_na_broj.data,
                    'model': form.model.data,
                    'stavke': []
                }

                # Extract stavke data
                for stavka_form in form.stavke:
                    stavka_data = {
                        'artikal_id': stavka_form.artikal_id.data,
                        'naziv': stavka_form.naziv.data,
                        'kolicina': stavka_form.kolicina.data,
                        'jedinica_mere': stavka_form.jedinica_mere.data,
                        'cena': stavka_form.cena.data
                    }
                    data['stavke'].append(stavka_data)

                current_app.logger.info(f'Updating faktura {faktura_id} with {len(data["stavke"])} stavke')

                # Update faktura using service
                updated_faktura = update_faktura(faktura.id, data, current_user)

                flash('Faktura uspešno ažurirana.', 'success')
                return redirect(url_for('fakture.detail', faktura_id=updated_faktura.id))

            except Exception as e:
                db.session.rollback()
                flash(f'Greška pri izmeni fakture: {str(e)}', 'danger')
                current_app.logger.error(f'Exception during faktura update: {str(e)}', exc_info=True)
                # Return form with existing data so user can fix errors
        else:
            # Form validation failed
            current_app.logger.warning('Form validation FAILED for edit faktura')
            current_app.logger.warning(f'Form errors: {form.errors}')
            flash('Forma sadrži greške. Molimo proverite unete podatke.', 'danger')
            # Display specific errors
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'warning')

    # GET request: Prepopulate form with existing data
    if request.method == 'GET':
        form.tip_fakture.data = faktura.tip_fakture
        form.valuta_fakture.data = faktura.valuta_fakture
        form.srednji_kurs.data = faktura.srednji_kurs
        form.komitent_id.data = faktura.komitent_id
        form.datum_prometa.data = faktura.datum_prometa
        form.valuta_placanja.data = faktura.valuta_placanja
        form.broj_ugovora.data = faktura.broj_ugovora
        form.broj_odluke.data = faktura.broj_odluke
        form.broj_narudzbenice.data = faktura.broj_narudzbenice
        form.poziv_na_broj.data = faktura.poziv_na_broj
        form.model.data = faktura.model
        # Story 4.4: Zatvaranje avansa
        form.zatvara_avans.data = bool(faktura.avansna_faktura_id)
        form.avansna_faktura_id.data = faktura.avansna_faktura_id

    # Load komitenti for dropdown (filtered by firma)
    komitenti = filter_by_firma(Komitent.query).all()

    return render_template('fakture/edit.html', form=form, komitenti=komitenti, faktura=faktura)


@fakture_bp.route('/<int:faktura_id>/finalizuj', methods=['POST'])
@login_required
def finalizuj(faktura_id):
    """
    Finalize draft invoice.

    Args:
        faktura_id: Invoice ID
    """
    try:
        # Get faktura with tenant isolation
        faktura = filter_by_firma(Faktura.query).filter_by(id=faktura_id).first_or_404()

        # Finalize using service
        finalize_faktura(faktura.id)

        flash('Faktura finalizovana i spremna za PDF generisanje.', 'success')

    except ValueError as e:
        flash(f'Greška: {str(e)}', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Greška pri finalizaciji fakture: {str(e)}', 'danger')

    return redirect(url_for('fakture.detail', faktura_id=faktura_id))


@fakture_bp.route('/<int:faktura_id>/storniraj', methods=['POST'])
@login_required
def storniraj(faktura_id):
    """
    Cancel (stornirati) an invoice and regenerate PDF with watermark.

    Args:
        faktura_id: Invoice ID

    Story: 4.5 - Storniranje Fakture
    """
    try:
        # Get razlog from form (optional)
        razlog = request.form.get('razlog', None)

        # Call service function (includes tenant isolation and authorization checks)
        faktura = storniraj_fakturu(faktura_id, razlog)

        # Trigger PDF regeneration with watermark (in background)
        if faktura.pdf_url:
            faktura.status_pdf = 'generating'
            db.session.commit()
            
            import celery_worker
            celery_worker.generate_faktura_pdf_task_async.apply_async(args=[faktura_id])

        flash(f'Faktura {faktura.broj_fakture} uspešno stornirana. PDF se regeneriše sa watermark-om.', 'success')
        return redirect(url_for('fakture.lista'))

    except ValueError as e:
        flash(f'Greška: {str(e)}', 'danger')
        return redirect(url_for('fakture.detail', faktura_id=faktura_id))

    except PermissionError as e:
        flash(f'Greška: {str(e)}', 'danger')
        return redirect(url_for('fakture.detail', faktura_id=faktura_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Greška pri storniranju fakture: {str(e)}', 'danger')
        return redirect(url_for('fakture.detail', faktura_id=faktura_id))


@fakture_bp.route('/<int:faktura_id>/download-pdf')
@login_required
def download_pdf(faktura_id):
    """
    Download PDF file for a finalized invoice.

    Args:
        faktura_id: Invoice ID

    Returns:
        PDF file or error message
    """
    # Get faktura with tenant isolation
    faktura = filter_by_firma(Faktura.query).filter_by(id=faktura_id).first_or_404()

    # Check if PDF exists
    if not faktura.pdf_url or faktura.status_pdf != 'generated':
        flash('PDF nije dostupan. Molimo pokušajte ponovo kasnije.', 'warning')
        return redirect(url_for('fakture.detail', faktura_id=faktura_id))

    # Convert relative path to absolute path (relative to project root)
    # If pdf_url is already absolute, use it directly
    if os.path.isabs(faktura.pdf_url):
        pdf_path = faktura.pdf_url
    else:
        # Create absolute path relative to project root (parent of app folder)
        project_root = os.path.dirname(current_app.root_path)
        pdf_path = os.path.join(project_root, faktura.pdf_url)

    # Check if file exists on disk
    if not os.path.exists(pdf_path):
        flash('PDF fajl nije pronađen. Molimo kontaktirajte podršku.', 'danger')
        return redirect(url_for('fakture.detail', faktura_id=faktura_id))

    # Generate filename for download (sanitize broj_fakture)
    safe_filename = faktura.broj_fakture.replace('/', '-')
    download_name = f'Faktura_{safe_filename}.pdf'

    # Serve PDF file
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=download_name,
        mimetype='application/pdf'
    )


@fakture_bp.route('/<int:faktura_id>/retry-pdf', methods=['POST'])
@login_required
def retry_pdf(faktura_id):
    """
    Retry PDF generation for a failed invoice.

    Args:
        faktura_id: Invoice ID

    Returns:
        JSON response with status
    """
    try:
        # Get faktura with tenant isolation
        faktura = filter_by_firma(Faktura.query).filter_by(id=faktura_id).first_or_404()

        # Set PDF status to 'generating'
        faktura.status_pdf = 'generating'
        db.session.commit()

        # Trigger background PDF generation
        import celery_worker
        celery_worker.generate_faktura_pdf_task_async.apply_async(args=[faktura_id])

        return jsonify({
            'success': True,
            'message': 'PDF generisanje u toku...'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Greška: {str(e)}'
        }), 500


@fakture_bp.route('/<int:faktura_id>/send-email', methods=['POST'])
@login_required
def send_email(faktura_id):
    """
    Send invoice via email with PDF attachment.

    Args:
        faktura_id: Invoice ID

    Returns:
        JSON response with status
    """
    try:
        # Get faktura with tenant isolation
        faktura = filter_by_firma(Faktura.query).filter_by(id=faktura_id).first_or_404()

        # Validate that invoice is finalized or cancelled (Story 4.5)
        if faktura.status not in ['izdata', 'stornirana']:
            return jsonify({
                'success': False,
                'error': 'Samo izdate i stornirane fakture mogu biti poslate'
            }), 400

        # Validate that PDF is generated
        if not faktura.pdf_url or faktura.status_pdf != 'generated':
            return jsonify({
                'success': False,
                'error': 'PDF nije dostupan. Molimo generišite PDF prvo.'
            }), 400

        # Get JSON payload
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Nedostaje JSON payload'
            }), 400

        recipient_email = data.get('recipient_email')
        cc_email = data.get('cc_email')
        custom_subject = data.get('subject')  # Get custom subject from user
        custom_body = data.get('body')  # Get custom body from user

        # Validate required fields
        if not recipient_email:
            return jsonify({
                'success': False,
                'error': 'Email primaoca je obavezan'
            }), 400

        # Use centralized email validation from email_service
        from app.services.email_service import validate_email_format, InvalidEmailError
        try:
            validate_email_format(recipient_email)
            if cc_email:
                validate_email_format(cc_email)
        except InvalidEmailError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400

        # Update status to 'sending'
        faktura.email_status = 'sending'
        faktura.email_recipient = recipient_email
        db.session.commit()

        # Trigger background email sending with user customization
        import celery_worker
        celery_worker.send_faktura_email_task_async.apply_async(
            args=[faktura_id, recipient_email, cc_email, custom_subject, custom_body]
        )

        return jsonify({
            'success': True,
            'message': 'Email se šalje...',
            'recipient_email': recipient_email
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Greška pri slanju email-a za fakturu {faktura_id}: {e}')
        return jsonify({
            'success': False,
            'error': f'Greška: {str(e)}'
        }), 500


@fakture_bp.route('/<int:faktura_id>/retry-email', methods=['POST'])
@login_required
def retry_email(faktura_id):
    """
    Retry email sending for a failed invoice.

    Args:
        faktura_id: Invoice ID

    Returns:
        JSON response with status
    """
    try:
        # Get faktura with tenant isolation
        faktura = filter_by_firma(Faktura.query).filter_by(id=faktura_id).first_or_404()

        # Validate that invoice was previously attempted to be sent
        if faktura.email_status not in ['failed', 'sent']:
            return jsonify({
                'success': False,
                'message': 'Email može biti ponovo poslat samo ako je prethodno neuspešan'
            }), 400

        # Validate that we have recipient email
        if not faktura.email_recipient:
            return jsonify({
                'success': False,
                'message': 'Email primaoca nije poznat'
            }), 400

        # Reset status to 'sending'
        faktura.email_status = 'sending'
        faktura.email_error_message = None
        db.session.commit()

        # Trigger background email sending with same recipient
        import celery_worker
        celery_worker.send_faktura_email_task_async.apply_async(
            args=[faktura_id, faktura.email_recipient, None, None, None]
        )

        return jsonify({
            'success': True,
            'message': 'Email se ponovo šalje...'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Greška pri ponovnom slanju email-a za fakturu {faktura_id}: {e}')
        return jsonify({
            'success': False,
            'message': f'Greška: {str(e)}'
        }), 500


@fakture_bp.route('/api/komitenti/search')
@login_required
def search_komitenti():
    """
    AJAX endpoint for komitent autocomplete search.

    Query Parameters:
        - q: str - Search query (searches in naziv and PIB)

    Returns:
        JSON array of matching komitenti: [{"id": 1, "naziv": "...", "pib": "..."}, ...]

    Security:
        - Tenant isolation applied (pausalac sees only their firma's komitenti)
    """
    query_str = request.args.get('q', '').strip()

    if not query_str:
        return jsonify([])

    # Search with tenant isolation
    search_term = f"%{query_str}%"
    komitenti = filter_by_firma(Komitent.query).filter(
        db.or_(
            Komitent.naziv.ilike(search_term),
            Komitent.pib.ilike(search_term)
        )
    ).limit(10).all()

    # Format response as JSON
    results = [
        {
            'id': k.id,
            'naziv': k.naziv,
            'pib': k.pib
        }
        for k in komitenti
    ]

    return jsonify(results)


@fakture_bp.route('/api/fakture/avansne/izdate')
@login_required
def get_avansne_izdate():
    """
    AJAX endpoint for listing issued avansne fakture (for zatvaranje avansa).

    Returns:
        JSON array of issued avansne fakture: [{"id": 1, "broj_fakture": "...",
        "komitent_naziv": "...", "iznos": 1000.00}, ...]

    Security:
        - Tenant isolation applied (pausalac sees only their firma's avansne fakture)
        - Only returns fakture with status='izdata' (not 'draft', 'zatvorena', etc.)

    Story: 4.4 - Zatvaranje Avansa
    """
    # Get all avansne fakture with status='izdata' (tenant isolation applied)
    avansne_fakture = filter_by_firma(Faktura.query).filter_by(
        tip_fakture='avansna',
        status='izdata'
    ).order_by(Faktura.datum_prometa.desc()).all()

    # Format response as JSON
    results = [
        {
            'id': f.id,
            'broj_fakture': f.broj_fakture,
            'komitent_naziv': f.komitent.naziv if f.komitent else 'N/A',
            'iznos': float(f.ukupan_iznos_rsd),
            'valuta': f.valuta_fakture
        }
        for f in avansne_fakture
    ]

    return jsonify(results)


@fakture_bp.route('/api/limit-widget-data', methods=['GET'])
@login_required
@limiter.limit("100 per minute")
def get_limit_widget_data():
    """
    API endpoint for limit tracking widget data.

    Query Parameters:
        - nova_faktura_iznos: float (optional) - Amount of new invoice for simulation

    Returns:
        JSON response with rolling limit data:
        {
            "rolling_limit": 8000000,
            "promet_365_dana": 4500000,
            "preostali_limit": 3500000,
            "progress_percentage": 56.25,
            "progress_color": "success",
            "projekcija_7": 3400000,
            "projekcija_15": 3300000,
            "projekcija_30": 3100000,
            "nova_faktura_iznos": 500000,
            "preostalo_nakon_nove": 3000000,
            "over_limit": false,
            "over_limit_amount": 0
        }

    Security:
        - Tenant isolation applied (pausalac sees only their firma's data)
        - Admin in firm context sees selected firma's data
        - Admin in god mode gets 400 error

    Story: 5.4 - Limit Tracking Widget
    """
    from app.utils.query_helpers import get_user_firma_id
    from app.services.dashboard_service import calculate_rolling_limit_projections, ROLLING_LIMIT_365_DAYS
    from datetime import date, timedelta
    from sqlalchemy import func, and_

    # Get firma_id with tenant isolation
    firma_id = get_user_firma_id()
    if firma_id is None:
        return jsonify({
            'error': 'Molimo selektujte firmu pre pristupa ovoj funkcionalnosti.'
        }), 400

    try:
        # Get rolling limit projections (reuse existing function)
        projections = calculate_rolling_limit_projections(firma_id)

        # Calculate promet_365_dana (needed for progress bar)
        date_365_days_ago = date.today() - timedelta(days=365)
        promet_365_dana = db.session.query(
            func.coalesce(func.sum(Faktura.ukupan_iznos_rsd), 0)
        ).filter(
            and_(
                Faktura.firma_id == firma_id,
                Faktura.datum_prometa >= date_365_days_ago,
                Faktura.status != 'stornirana'
            )
        ).scalar()

        promet_365_dana = float(promet_365_dana or 0)
        preostali_limit = float(projections['preostali_limit'])

        # Calculate progress percentage and color
        progress_percentage = (promet_365_dana / ROLLING_LIMIT_365_DAYS) * 100 if ROLLING_LIMIT_365_DAYS > 0 else 0

        # Determine progress color based on percentage
        if progress_percentage < 70:
            progress_color = 'success'
        elif progress_percentage < 90:
            progress_color = 'warning'
        else:
            progress_color = 'danger'

        # Build base response
        response_data = {
            'rolling_limit': ROLLING_LIMIT_365_DAYS,
            'promet_365_dana': promet_365_dana,
            'preostali_limit': preostali_limit,
            'progress_percentage': round(progress_percentage, 2),
            'progress_color': progress_color,
            'projekcija_7': float(projections['projekcija_7_dana']),
            'projekcija_15': float(projections['projekcija_15_dana']),
            'projekcija_30': float(projections['projekcija_30_dana'])
        }

        # Handle nova_faktura_iznos parameter (simulation)
        nova_faktura_iznos = request.args.get('nova_faktura_iznos', 0, type=float)

        if nova_faktura_iznos > 0:
            # Calculate new limit after adding nova faktura
            preostalo_nakon_nove = preostali_limit - nova_faktura_iznos
            over_limit = preostalo_nakon_nove < 0

            response_data['nova_faktura_iznos'] = nova_faktura_iznos
            response_data['preostalo_nakon_nove'] = preostalo_nakon_nove
            response_data['over_limit'] = over_limit
            response_data['over_limit_amount'] = abs(preostalo_nakon_nove) if over_limit else 0
        else:
            # No simulation
            response_data['nova_faktura_iznos'] = 0
            response_data['preostalo_nakon_nove'] = preostali_limit
            response_data['over_limit'] = False
            response_data['over_limit_amount'] = 0

        return jsonify(response_data), 200

    except Exception as e:
        current_app.logger.error(f'Error fetching limit widget data for firma {firma_id}: {e}', exc_info=True)
        return jsonify({
            'error': f'Greška pri učitavanju podataka: {str(e)}'
        }), 500


@fakture_bp.route('/<int:faktura_id>/konvertuj', methods=['POST'])
@login_required
def konvertuj_profakturu(faktura_id):
    """
    Convert profaktura to standard faktura.

    Route: POST /fakture/<id>/konvertuj

    Business Rules:
        - Only izdate profakture can be converted
        - Conversion creates new draft faktura
        - Profaktura status changes to 'konvertovana'
        - User is redirected to new faktura detail page

    Returns:
        Redirect to new faktura detail page with success message

    Security:
        - Tenant isolation applied (user can only convert their firma's profakture)
    """
    # Load profaktura with tenant isolation
    profaktura = filter_by_firma(Faktura.query).filter_by(id=faktura_id).first()

    if not profaktura:
        flash('Profaktura nije pronađena.', 'danger')
        return redirect(url_for('fakture.lista'))

    try:
        # Convert profaktura to standard faktura
        nova_faktura = convert_profaktura_to_faktura(profaktura.id)

        # Success message with new faktura broj
        flash(
            f'Profaktura uspešno konvertovana u fakturu {nova_faktura.broj_fakture}.',
            'success'
        )

        # Redirect to new faktura detail page
        return redirect(url_for('fakture.detail', faktura_id=nova_faktura.id))

    except ValueError as e:
        # Handle validation errors (e.g., profaktura nije izdata, već konvertovana, etc.)
        flash(str(e), 'danger')
        return redirect(url_for('fakture.detail', faktura_id=profaktura.id))

    except Exception as e:
        # Handle unexpected errors
        db.session.rollback()
        current_app.logger.error(f'Error converting profaktura {faktura_id}: {e}')
        flash('Greška pri konverziji profakture. Molimo pokušajte ponovo.', 'danger')
        return redirect(url_for('fakture.detail', faktura_id=profaktura.id))

