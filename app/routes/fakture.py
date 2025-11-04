"""Routes for Fakture (Invoices) management."""
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_login import login_required, current_user
from app import db
from app.models.faktura import Faktura
from app.models.komitent import Komitent
from app.forms.faktura import FakturaCreateForm
from app.services.faktura_service import create_faktura, update_faktura, finalize_faktura
from app.utils.query_helpers import filter_by_firma

fakture_bp = Blueprint('fakture', __name__, url_prefix='/fakture')


@fakture_bp.route('/')
@login_required
def lista():
    """
    Display list of all invoices for current user's firma.

    Returns paginated list of invoices sorted by creation date (newest first).
    """
    # Get all fakture for current firma (with tenant isolation)
    fakture = filter_by_firma(Faktura.query).order_by(Faktura.created_at.desc()).all()

    return render_template('fakture/lista.html', fakture=fakture)


@fakture_bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova_faktura():
    """
    Create new invoice form.

    GET: Display form
    POST: Create draft invoice
    """
    form = FakturaCreateForm()

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

                flash('Faktura kreirana kao nacrt.', 'success')
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

        # Validate that invoice is finalized
        if faktura.status != 'izdata':
            return jsonify({
                'success': False,
                'error': 'Samo izdate fakture mogu biti poslate'
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
