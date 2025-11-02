"""Unit tests for PDF service."""
import pytest
import os
from unittest.mock import patch, MagicMock, mock_open
from datetime import date
from decimal import Decimal

from app import db
from app.models import User, PausalnFirma, Komitent, Faktura
from app.services import pdf_service


class TestGetTemplate:
    """Tests for get_template function."""

    def test_get_template_returns_srpski_for_domestic(self, app):
        """Test get_template returns Serbian template for jezik='sr'."""
        with app.app_context():
            # Create faktura with serbian language
            faktura = Faktura(jezik='sr')

            template = pdf_service.get_template(faktura)

            assert template == 'pdf/faktura_sr.html'

    def test_get_template_returns_engleski_for_foreign(self, app):
        """Test get_template returns English template for jezik='en'."""
        with app.app_context():
            # Create faktura with english language
            faktura = Faktura(jezik='en')

            template = pdf_service.get_template(faktura)

            assert template == 'pdf/faktura_en.html'


class TestEnsureStorageFolder:
    """Tests for ensure_storage_folder function."""

    def test_ensure_storage_folder_creates_path(self, app):
        """Test ensure_storage_folder creates correct folder structure."""
        with app.app_context():
            folder_path = pdf_service.ensure_storage_folder(1, 2025, 1)

            expected_path = os.path.join('storage', 'fakture', '1', '2025', '01')
            assert folder_path == expected_path
            assert os.path.exists(folder_path)

    def test_ensure_storage_folder_handles_existing(self, app):
        """Test ensure_storage_folder works with existing folders."""
        with app.app_context():
            # Create folder first time
            folder_path1 = pdf_service.ensure_storage_folder(2, 2025, 3)

            # Create same folder again (should not raise error)
            folder_path2 = pdf_service.ensure_storage_folder(2, 2025, 3)

            assert folder_path1 == folder_path2
            assert os.path.exists(folder_path2)


class TestGeneratePdf:
    """Tests for generate_pdf function."""

    def test_generate_pdf_with_serbian_characters_xhtml2pdf(self, app):
        """Test PDF generation with Serbian characters using xhtml2pdf fallback."""
        with app.app_context():
            # Create dependencies with Serbian characters
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Ćevabdžinica Šećer',
                adresa='Đušina',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=['123-456-789']
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id,
                pib='98765432',
                maticni_broj='12348765',
                naziv='Komitent Žarković',
                adresa='Čačak',
                broj='2',
                postanski_broj='32000',
                mesto='Čačak',
                drzava='Srbija',
                email='k@test.rs'
            )
            db.session.add(komitent)

            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create faktura
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='ČŠĆ-001/2025',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                jezik='sr',
                datum_prometa=date(2025, 1, 15),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 14),
                ukupan_iznos_rsd=Decimal('100.00')
            )
            db.session.add(faktura)
            db.session.commit()

            # Generate PDF (should use xhtml2pdf fallback on Windows)
            pdf_bytes = pdf_service.generate_pdf(faktura)

            # Assertions
            assert pdf_bytes is not None
            assert len(pdf_bytes) > 0
            assert pdf_bytes.startswith(b'%PDF')  # PDF magic number

    @pytest.mark.skip(reason="WeasyPrint requires GTK dependencies not available on Windows")
    @patch('app.services.pdf_service.render_pdf_template')
    @patch('weasyprint.HTML')
    def test_generate_pdf_domestic_faktura(self, mock_html, mock_render, app):
        """Test PDF generation for domestic invoice uses Serbian template."""
        with app.app_context():
            # Setup mocks
            mock_render.return_value = '<html>Faktura HTML</html>'
            mock_pdf_instance = MagicMock()
            mock_pdf_instance.write_pdf.return_value = b'PDF_BYTES'
            mock_html.return_value = mock_pdf_instance

            # Create faktura
            faktura = Faktura(jezik='sr')

            # Generate PDF
            result = pdf_service.generate_pdf(faktura)

            # Assertions
            assert result == b'PDF_BYTES'
            mock_render.assert_called_once_with(faktura, 'pdf/faktura_sr.html')
            mock_html.assert_called_once_with(string='<html>Faktura HTML</html>')
            mock_pdf_instance.write_pdf.assert_called_once()

    @pytest.mark.skip(reason="WeasyPrint requires GTK dependencies not available on Windows")
    @patch('app.services.pdf_service.render_pdf_template')
    @patch('weasyprint.HTML')
    def test_generate_pdf_foreign_faktura(self, mock_html, mock_render, app):
        """Test PDF generation for foreign invoice uses English template."""
        with app.app_context():
            # Setup mocks
            mock_render.return_value = '<html>Invoice HTML</html>'
            mock_pdf_instance = MagicMock()
            mock_pdf_instance.write_pdf.return_value = b'PDF_BYTES'
            mock_html.return_value = mock_pdf_instance

            # Create faktura
            faktura = Faktura(jezik='en')

            # Generate PDF
            result = pdf_service.generate_pdf(faktura)

            # Assertions
            assert result == b'PDF_BYTES'
            mock_render.assert_called_once_with(faktura, 'pdf/faktura_en.html')
            mock_html.assert_called_once_with(string='<html>Invoice HTML</html>')

    @pytest.mark.skip(reason="WeasyPrint requires GTK dependencies not available on Windows")
    @patch('weasyprint.HTML')
    def test_pdf_generation_fails_gracefully(self, mock_html, app):
        """Test PDF generation raises ValueError on failure."""
        with app.app_context():
            # Setup mock to raise exception
            mock_html.side_effect = Exception('WeasyPrint error')

            # Create faktura
            faktura = Faktura(jezik='sr')

            # Should raise ValueError
            with pytest.raises(ValueError) as exc_info:
                pdf_service.generate_pdf(faktura)

            assert 'PDF generation failed' in str(exc_info.value)
            assert 'WeasyPrint error' in str(exc_info.value)


class TestSavePdf:
    """Tests for save_pdf function."""

    def test_save_pdf_creates_folder_structure(self, app):
        """Test save_pdf creates folder structure."""
        with app.app_context():
            # Create dependencies
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id,
                pib='98765432',
                maticni_broj='12348765',
                naziv='Komitent',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='k@test.rs'
            )
            db.session.add(komitent)

            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create faktura
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='001/2025',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 15),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 14),
                ukupan_iznos_rsd=Decimal('100.00')
            )
            db.session.add(faktura)
            db.session.commit()

            # Save PDF
            pdf_bytes = b'FAKE_PDF_CONTENT'
            file_path = pdf_service.save_pdf(pdf_bytes, faktura)

            # Check folder exists
            expected_folder = os.path.join('storage', 'fakture', str(firma.id), '2025', '01')
            assert os.path.exists(expected_folder)

            # Check file was created
            assert os.path.exists(file_path)
            assert file_path.endswith('001-2025.pdf')

            # Clean up
            if os.path.exists(file_path):
                os.remove(file_path)

    def test_save_pdf_updates_faktura_pdf_url(self, app):
        """Test save_pdf updates faktura.pdf_url in database."""
        with app.app_context():
            # Create dependencies
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id,
                pib='98765432',
                maticni_broj='12348765',
                naziv='Komitent',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='k@test.rs'
            )
            db.session.add(komitent)

            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create faktura
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='MK-002/2025',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 3, 10),
                valuta_placanja=30,
                datum_dospeca=date(2025, 4, 9),
                ukupan_iznos_rsd=Decimal('250.00')
            )
            db.session.add(faktura)
            db.session.commit()

            # Initial state
            assert faktura.pdf_url is None
            assert faktura.status_pdf == 'pending'

            # Save PDF
            pdf_bytes = b'FAKE_PDF_CONTENT_2'
            file_path = pdf_service.save_pdf(pdf_bytes, faktura)

            # Refresh faktura from DB
            db.session.refresh(faktura)

            # Check updates
            assert faktura.pdf_url == file_path
            assert faktura.status_pdf == 'generated'
            assert 'MK-002-2025.pdf' in faktura.pdf_url

            # Clean up
            if os.path.exists(file_path):
                os.remove(file_path)
