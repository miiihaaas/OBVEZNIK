"""
Unit tests for custom exception classes
Story 5.7 - Error Handling & User Feedback
"""
import pytest
from app.utils.exceptions import (
    APIError,
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    ServerError,
    DatabaseError,
    BusinessLogicError,
    DuplicateError
)


class TestAPIError:
    """Test base APIError class"""

    def test_api_error_default_status_code(self):
        """Test that APIError has default status code 500"""
        error = APIError("Test error")
        assert error.status_code == 500
        assert error.message == "Test error"

    def test_api_error_custom_status_code(self):
        """Test that APIError accepts custom status code"""
        error = APIError("Test error", status_code=418)
        assert error.status_code == 418

    def test_api_error_with_payload(self):
        """Test that APIError can store additional payload"""
        error = APIError("Test error", payload={'field': 'email', 'value': 'invalid'})
        assert error.payload == {'field': 'email', 'value': 'invalid'}

    def test_api_error_to_dict(self):
        """Test that APIError can be converted to dictionary"""
        error = APIError("Test error", status_code=400, payload={'field': 'email'})
        result = error.to_dict()

        assert result['error'] == "Test error"
        assert result['status_code'] == 400
        assert result['field'] == 'email'


class TestValidationError:
    """Test ValidationError class (400 Bad Request)"""

    def test_validation_error_status_code(self):
        """Test that ValidationError has status code 400"""
        error = ValidationError("PIB mora biti 8 ili 9 cifara")
        assert error.status_code == 400
        assert error.message == "PIB mora biti 8 ili 9 cifara"

    def test_validation_error_with_field_payload(self):
        """Test ValidationError with field information"""
        error = ValidationError("Email adresa nije validna", payload={'field': 'email'})
        result = error.to_dict()

        assert result['error'] == "Email adresa nije validna"
        assert result['field'] == 'email'


class TestNotFoundError:
    """Test NotFoundError class (404 Not Found)"""

    def test_not_found_error_status_code(self):
        """Test that NotFoundError has status code 404"""
        error = NotFoundError("Faktura sa ID 123 nije pronađena")
        assert error.status_code == 404
        assert error.message == "Faktura sa ID 123 nije pronađena"


class TestUnauthorizedError:
    """Test UnauthorizedError class (403 Forbidden)"""

    def test_unauthorized_error_status_code(self):
        """Test that UnauthorizedError has status code 403"""
        error = UnauthorizedError("Nemate dozvolu za pristup ovoj fakturi")
        assert error.status_code == 403
        assert error.message == "Nemate dozvolu za pristup ovoj fakturi"


class TestServerError:
    """Test ServerError class (500 Internal Server Error)"""

    def test_server_error_status_code(self):
        """Test that ServerError has status code 500"""
        error = ServerError("Greška pri generisanju PDF-a")
        assert error.status_code == 500
        assert error.message == "Greška pri generisanju PDF-a"


class TestDatabaseError:
    """Test DatabaseError class"""

    def test_database_error_inherits_from_server_error(self):
        """Test that DatabaseError inherits from ServerError"""
        error = DatabaseError("Greška pri čuvanju podataka")
        assert error.status_code == 500
        assert isinstance(error, ServerError)

    def test_database_error_with_original_exception(self):
        """Test DatabaseError can store original exception"""
        original = Exception("Connection timeout")
        error = DatabaseError("Greška pri čuvanju podataka", original_exception=original)

        assert error.message == "Greška pri čuvanju podataka"
        assert error.original_exception == original


class TestBusinessLogicError:
    """Test BusinessLogicError class"""

    def test_business_logic_error_inherits_from_validation_error(self):
        """Test that BusinessLogicError inherits from ValidationError"""
        error = BusinessLogicError("Prekoračen limit prihoda")
        assert error.status_code == 400
        assert isinstance(error, ValidationError)


class TestDuplicateError:
    """Test DuplicateError class"""

    def test_duplicate_error_inherits_from_validation_error(self):
        """Test that DuplicateError inherits from ValidationError"""
        error = DuplicateError("Komitent sa PIB-om 12345678 već postoji")
        assert error.status_code == 400
        assert isinstance(error, ValidationError)

    def test_duplicate_error_message(self):
        """Test DuplicateError message"""
        error = DuplicateError("Email adresa je već u upotrebi")
        assert error.message == "Email adresa je već u upotrebi"
