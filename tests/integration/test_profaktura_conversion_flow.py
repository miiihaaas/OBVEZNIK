"""Integration tests for Profaktura Conversion Flow."""
import pytest
from datetime import date
from decimal import Decimal
from flask import url_for

from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.komitent import Komitent
from app.models.faktura import Faktura
from app.services.faktura_service import create_faktura, finalize_faktura


@pytest.fixture
def pausalac_with_firma(app):
    """Create a test pausalac user with firma."""
    with app.app_context():
        firma = PausalnFirma(
            pib='123456789',
            maticni_broj='12345678',
            naziv='Test Firma',
            adresa='Test Adresa',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            telefon='011111111',
            email='firma@test.com',
            dinarski_racuni=[{'banka': 'Test Banka', 'racun': '123-456789-00'}],
            prefiks_fakture='TF-',
            sufiks_fakture='/2025',
            brojac_fakture=1,
            brojac_profakture=1
        )
        db.session.add(firma)
        db.session.commit()

        user = User(
            email='pausalac@test.com',
            full_name='Test Pausalac',
            role='pausalac',
            firma_id=firma.id
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        yield user, firma


@pytest.fixture
def komitent(pausalac_with_firma):
    """Create a test komitent for the pausalac's firma."""
    user, firma = pausalac_with_firma
    komitent = Komitent(
        firma_id=firma.id,
        pib='87654321',
        maticni_broj='12345678',
        naziv='Test Komitent',
        adresa='Komitent Adresa',
        broj='2',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        email='komitent@test.rs'
    )
    db.session.add(komitent)
    db.session.commit()
    return komitent


class TestProfakturaConversionFlow:
    """Integration tests for profaktura conversion flow."""

    def test_pausalac_can_convert_profaktura_to_faktura(self, client, pausalac_with_firma, komitent):
        """Test complete flow: create profaktura, finalize, convert to faktura."""
        user, firma = pausalac_with_firma

        # Login as pausalac
        client.post('/login', data={
            'email': 'pausalac@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Create and finalize profaktura via service (simulating form submission)
        profaktura_data = {
            'tip_fakture': 'profaktura',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 1, 15),
            'valuta_placanja': 7,
            'stavke': [
                {'naziv': 'Usluga 1', 'kolicina': 2, 'jedinica_mere': 'h', 'cena': Decimal('100.00')},
                {'naziv': 'Usluga 2', 'kolicina': 1, 'jedinica_mere': 'kom', 'cena': Decimal('50.00')}
            ]
        }

        profaktura = create_faktura(profaktura_data, user)
        finalize_faktura(profaktura.id)

        # Convert profaktura to faktura via POST request
        response = client.post(
            f'/fakture/{profaktura.id}/konvertuj',
            follow_redirects=True
        )

        # Assertions
        assert response.status_code == 200
        assert 'uspešno konvertovana' in response.data.decode('utf-8')

        # Check profaktura status changed
        db.session.refresh(profaktura)
        assert profaktura.status == 'konvertovana'
        assert profaktura.konvertovana_u_fakturu_id is not None

        # Check new faktura created
        nova_faktura = Faktura.query.get(profaktura.konvertovana_u_fakturu_id)
        assert nova_faktura is not None
        assert nova_faktura.tip_fakture == 'standardna'
        assert nova_faktura.status == 'draft'

    def test_conversion_redirects_to_new_faktura_detail(self, client, pausalac_with_firma, komitent):
        """Test that conversion redirects to new faktura detail page."""
        user, firma = pausalac_with_firma

        # Login
        client.post('/login', data={
            'email': 'pausalac@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Create and finalize profaktura
        profaktura_data = {
            'tip_fakture': 'profaktura',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 1, 15),
            'valuta_placanja': 7,
            'stavke': [
                {'naziv': 'Usluga', 'kolicina': 1, 'jedinica_mere': 'h', 'cena': Decimal('100.00')}
            ]
        }

        profaktura = create_faktura(profaktura_data, user)
        finalize_faktura(profaktura.id)

        # Convert profaktura
        response = client.post(
            f'/fakture/{profaktura.id}/konvertuj',
            follow_redirects=False  # Don't follow redirect
        )

        # Check redirect
        assert response.status_code == 302
        assert '/fakture/' in response.location
        # Should redirect to new faktura detail, not profaktura detail
        assert f'/fakture/{profaktura.id}' not in response.location

    def test_conversion_shows_success_message(self, client, pausalac_with_firma, komitent):
        """Test that conversion shows success flash message."""
        user, firma = pausalac_with_firma

        # Login
        client.post('/login', data={
            'email': 'pausalac@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Create and finalize profaktura
        profaktura_data = {
            'tip_fakture': 'profaktura',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 1, 15),
            'valuta_placanja': 7,
            'stavke': [
                {'naziv': 'Usluga', 'kolicina': 1, 'jedinica_mere': 'h', 'cena': Decimal('100.00')}
            ]
        }

        profaktura = create_faktura(profaktura_data, user)
        finalize_faktura(profaktura.id)

        # Convert profaktura
        response = client.post(
            f'/fakture/{profaktura.id}/konvertuj',
            follow_redirects=True
        )

        # Check success message
        assert 'uspešno konvertovana' in response.data.decode('utf-8')

    def test_cannot_convert_draft_profaktura(self, client, pausalac_with_firma, komitent):
        """Test that draft profaktura cannot be converted."""
        user, firma = pausalac_with_firma

        # Login
        client.post('/login', data={
            'email': 'pausalac@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Create profaktura but DON'T finalize
        profaktura_data = {
            'tip_fakture': 'profaktura',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 1, 15),
            'valuta_placanja': 7,
            'stavke': [
                {'naziv': 'Usluga', 'kolicina': 1, 'jedinica_mere': 'h', 'cena': Decimal('100.00')}
            ]
        }

        profaktura = create_faktura(profaktura_data, user)
        # Do NOT finalize - keep as draft

        # Try to convert
        response = client.post(
            f'/fakture/{profaktura.id}/konvertuj',
            follow_redirects=True
        )

        # Check error message
        assert 'Samo izdate profakture mogu biti konvertovane' in response.data.decode('utf-8')

    def test_cannot_convert_already_converted_profaktura(self, client, pausalac_with_firma, komitent):
        """Test that already converted profaktura cannot be converted again."""
        user, firma = pausalac_with_firma

        # Login
        client.post('/login', data={
            'email': 'pausalac@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Create and finalize profaktura
        profaktura_data = {
            'tip_fakture': 'profaktura',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 1, 15),
            'valuta_placanja': 7,
            'stavke': [
                {'naziv': 'Usluga', 'kolicina': 1, 'jedinica_mere': 'h', 'cena': Decimal('100.00')}
            ]
        }

        profaktura = create_faktura(profaktura_data, user)
        finalize_faktura(profaktura.id)

        # First conversion - should work
        client.post(f'/fakture/{profaktura.id}/konvertuj', follow_redirects=True)

        # Second conversion attempt - should fail
        response = client.post(
            f'/fakture/{profaktura.id}/konvertuj',
            follow_redirects=True
        )

        # Check error message
        assert 'već konvertovana' in response.data.decode('utf-8')

    def test_tenant_isolation_in_conversion(self, client, pausalac_with_firma, komitent):
        """Test that pausalac cannot convert profaktura from another firma."""
        user, firma = pausalac_with_firma

        # Create another firma and user
        other_firma = PausalnFirma(
            pib='987654321',
            maticni_broj='87654321',
            naziv='Other Firma',
            adresa='Other Adresa',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            telefon='011111112',
            email='other@test.com',
            dinarski_racuni=[{'banka': 'Other Banka', 'racun': '987-654321-00'}],
            prefiks_fakture='OF-',
            sufiks_fakture='/2025',
            brojac_fakture=1,
            brojac_profakture=1
        )
        db.session.add(other_firma)
        db.session.commit()

        other_user = User(
            email='other@test.com',
            full_name='Other User',
            role='pausalac',
            firma_id=other_firma.id
        )
        other_user.set_password('password123')
        db.session.add(other_user)
        db.session.commit()

        # Create komitent for other firma
        other_komitent = Komitent(
            firma_id=other_firma.id,
            pib='11111111',
            maticni_broj='11111111',
            naziv='Other Komitent',
            adresa='Other Komitent Adresa',
            broj='3',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            email='other_komitent@test.rs'
        )
        db.session.add(other_komitent)
        db.session.commit()

        # Create and finalize profaktura for other firma
        profaktura_data = {
            'tip_fakture': 'profaktura',
            'valuta_fakture': 'RSD',
            'komitent_id': other_komitent.id,
            'datum_prometa': date(2025, 1, 15),
            'valuta_placanja': 7,
            'stavke': [
                {'naziv': 'Usluga', 'kolicina': 1, 'jedinica_mere': 'h', 'cena': Decimal('100.00')}
            ]
        }

        other_profaktura = create_faktura(profaktura_data, other_user)
        finalize_faktura(other_profaktura.id)

        # Login as first pausalac
        client.post('/login', data={
            'email': 'pausalac@test.com',
            'password': 'password123'
        }, follow_redirects=True)

        # Try to convert other firma's profaktura
        response = client.post(
            f'/fakture/{other_profaktura.id}/konvertuj',
            follow_redirects=True
        )

        # Check error - profaktura not found (tenant isolation)
        assert 'nije pronađena' in response.data.decode('utf-8')
