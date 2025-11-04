"""Unit tests for email service."""
import pytest
from unittest.mock import Mock, patch, mock_open
from app.services import email_service


@pytest.fixture
def sample_faktura():
    """Create a mock faktura for testing (domestic/Serbian)."""
    faktura = Mock()
    faktura.broj_fakture = "TEST-001/2025"
    faktura.tip_fakture = "standardna"
    faktura.valuta_fakture = "RSD"
    faktura.jezik = "sr"
    faktura.pdf_url = "/tmp/test_faktura.pdf"
    faktura.status = "izdata"
    faktura.status_pdf = "generated"
    faktura.ukupan_iznos_rsd = 10000.00

    # Mock firma relationship
    faktura.firma = Mock()
    faktura.firma.naziv = "Test Firma"

    # Mock komitent relationship
    faktura.komitent = Mock()
    faktura.komitent.naziv = "Test Komitent"
    faktura.komitent.email = "komitent@example.com"

    return faktura


@pytest.fixture
def devizna_faktura():
    """Create a mock foreign currency faktura for testing."""
    faktura = Mock()
    faktura.broj_fakture = "TEST-002/2025"
    faktura.tip_fakture = "devizna"
    faktura.valuta_fakture = "EUR"
    faktura.jezik = "en"
    faktura.pdf_url = "/tmp/test_faktura.pdf"
    faktura.status = "izdata"
    faktura.status_pdf = "generated"
    faktura.ukupan_iznos_rsd = 120000.00
    faktura.ukupan_iznos_originalna_valuta = 1000.00
    faktura.srednji_kurs = 120.0

    # Mock firma relationship
    faktura.firma = Mock()
    faktura.firma.naziv = "Test Firma"

    # Mock komitent relationship
    faktura.komitent = Mock()
    faktura.komitent.naziv = "Test Komitent"
    faktura.komitent.email = "komitent@example.com"

    return faktura


class TestEmailService:
    """Test cases for email service."""

    @patch('app.services.email_service.render_template')
    @patch('app.services.email_service.mail.send')
    @patch('builtins.open', new_callable=mock_open, read_data=b'PDF content')
    @patch('os.path.exists')
    def test_send_faktura_email_success(self, mock_exists, mock_file, mock_mail_send, mock_render, sample_faktura, app):
        """Test successful email sending."""
        with app.app_context():
            mock_exists.return_value = True
            mock_render.return_value = '<html>Test email body</html>'

            result = email_service.send_faktura_email(
                sample_faktura,
                'recipient@example.com',
                cc_email='cc@example.com'
            )

            assert result is True
            mock_mail_send.assert_called_once()

            # Verify that email was constructed correctly
            call_args = mock_mail_send.call_args
            message = call_args[0][0]
            assert 'recipient@example.com' in message.recipients
            assert 'cc@example.com' in message.cc

    def test_send_faktura_email_pdf_not_found(self, sample_faktura, app):
        """Test error when PDF file doesn't exist."""
        with app.app_context():
            sample_faktura.pdf_url = None

            with pytest.raises(FileNotFoundError) as exc_info:
                email_service.send_faktura_email(sample_faktura, 'test@example.com')

            assert 'PDF nije generisan' in str(exc_info.value)

    @patch('os.path.exists')
    def test_send_faktura_email_pdf_file_missing(self, mock_exists, sample_faktura, app):
        """Test error when PDF file is missing from disk."""
        with app.app_context():
            mock_exists.return_value = False

            with pytest.raises(FileNotFoundError) as exc_info:
                email_service.send_faktura_email(sample_faktura, 'test@example.com')

            assert 'PDF fajl ne postoji' in str(exc_info.value)

    def test_validate_email_format_valid(self, app):
        """Test email format validation with valid email."""
        with app.app_context():
            result = email_service.validate_email_format('test@example.com')
            assert result is True

    def test_validate_email_format_invalid(self, app):
        """Test email format validation with invalid email."""
        with app.app_context():
            with pytest.raises(email_service.InvalidEmailError):
                email_service.validate_email_format('invalid-email')

            with pytest.raises(email_service.InvalidEmailError):
                email_service.validate_email_format('test@')

            with pytest.raises(email_service.InvalidEmailError):
                email_service.validate_email_format('@example.com')

    def test_generate_email_subject(self, sample_faktura, app):
        """Test email subject generation."""
        with app.app_context():
            subject = email_service.generate_email_subject(sample_faktura)

            assert 'TEST-001/2025' in subject
            assert 'Test Firma' in subject

    def test_generate_email_subject_custom(self, sample_faktura, app):
        """Test email subject generation with custom subject."""
        with app.app_context():
            custom_subject = 'Custom Subject'
            subject = email_service.generate_email_subject(sample_faktura, custom_subject)

            assert subject == custom_subject

    @patch('app.services.email_service.render_template')
    def test_email_template_domestic_faktura(self, mock_render, sample_faktura, app):
        """Test email template for domestic faktura (Serbian)."""
        with app.app_context():
            mock_render.return_value = '<html>Serbian template</html>'

            result = email_service.get_email_template(sample_faktura)

            mock_render.assert_called_once_with('fakture/email/faktura_sr.html', faktura=sample_faktura)
            assert 'Serbian template' in result

    @patch('app.services.email_service.render_template')
    def test_email_template_foreign_faktura(self, mock_render, devizna_faktura, app):
        """Test email template for foreign faktura (English)."""
        with app.app_context():
            mock_render.return_value = '<html>English template</html>'

            result = email_service.get_email_template(devizna_faktura)

            mock_render.assert_called_once_with('fakture/email/faktura_en.html', faktura=devizna_faktura)
            assert 'English template' in result

    @patch('app.services.email_service.render_template')
    def test_email_template_custom_body(self, mock_render, sample_faktura, app):
        """Test email template with custom body."""
        with app.app_context():
            custom_body = '<html>Custom body</html>'

            result = email_service.get_email_template(sample_faktura, custom_body)

            mock_render.assert_not_called()
            assert result == custom_body
