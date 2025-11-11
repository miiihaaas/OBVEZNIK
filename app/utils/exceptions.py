"""
Custom Exception Classes for OBVEZNIK Application
Provides standardized error handling with HTTP status codes
"""


class APIError(Exception):
    """
    Base API Error class
    All custom exceptions inherit from this class
    """
    status_code = 500

    def __init__(self, message, status_code=None, payload=None):
        """
        Initialize API Error

        Args:
            message (str): Error message to display to user
            status_code (int, optional): HTTP status code (default: 500)
            payload (dict, optional): Additional error context data
        """
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        """
        Convert exception to dictionary for JSON response

        Returns:
            dict: Error response dictionary
        """
        rv = dict(self.payload or ())
        rv['error'] = self.message
        rv['status_code'] = self.status_code
        return rv


class ValidationError(APIError):
    """
    400 Bad Request - Validation errors (user input errors)

    Usage:
        raise ValidationError('PIB mora biti 8 ili 9 cifara')
        raise ValidationError('Email adresa nije validna', payload={'field': 'email'})
    """
    status_code = 400


class NotFoundError(APIError):
    """
    404 Not Found - Resource not found

    Usage:
        raise NotFoundError('Faktura sa ID 123 nije pronađena')
        raise NotFoundError('Komitent ne postoji')
    """
    status_code = 404


class UnauthorizedError(APIError):
    """
    403 Forbidden - Permission denied

    Usage:
        raise UnauthorizedError('Nemate dozvolu za pristup ovoj fakturi')
        raise UnauthorizedError('Admin prava su potrebna za ovu akciju')
    """
    status_code = 403


class ServerError(APIError):
    """
    500 Internal Server Error - Unexpected server errors

    Usage:
        raise ServerError('Greška pri generisanju PDF-a')
        raise ServerError('Database connection failed')
    """
    status_code = 500


class DatabaseError(ServerError):
    """
    500 Internal Server Error - Database-specific errors

    Usage:
        raise DatabaseError('Greška pri čuvanju podataka u bazu')
    """
    def __init__(self, message, original_exception=None):
        super().__init__(message)
        self.original_exception = original_exception


class BusinessLogicError(ValidationError):
    """
    400 Bad Request - Business logic validation errors

    Usage:
        raise BusinessLogicError('Prekoračen limit prihoda za paušalnu firmu')
        raise BusinessLogicError('Ne možete stornirati već storniranu fakturu')
    """
    pass


class DuplicateError(ValidationError):
    """
    400 Bad Request - Duplicate resource errors

    Usage:
        raise DuplicateError('Komitent sa PIB-om 12345678 već postoji')
        raise DuplicateError('Email adresa je već u upotrebi')
    """
    pass
