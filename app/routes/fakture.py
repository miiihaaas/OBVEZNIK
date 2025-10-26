"""Routes for Fakture (Invoices) management."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.faktura import Faktura
from app.models.komitent import Komitent
from app.forms.faktura import FakturaCreateForm
from app.services.faktura_service import create_faktura, finalize_faktura
from app.utils.query_helpers import filter_by_firma

fakture_bp = Blueprint('fakture', __name__, url_prefix='/fakture')


@fakture_bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova_faktura():
    """
    Create new invoice form.

    GET: Display form
    POST: Create draft invoice
    """
    form = FakturaCreateForm()

    if request.method == 'POST' and form.validate_on_submit():
        try:
            # Extract form data
            data = {
                'tip_fakture': form.tip_fakture.data,
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

            # Create faktura using service
            faktura = create_faktura(data, current_user)

            flash('Faktura kreirana kao nacrt.', 'success')
            return redirect(url_for('fakture.detail', faktura_id=faktura.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Greška pri kreiranju fakture: {str(e)}', 'danger')

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
