from fastapi import status
from typing import Optional, Dict, Any


class APIBusinessException(Exception):
    """Base exception for API business logic errors with HTTP-aware attributes."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        context: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.context = context
        self.details = details or {}
        super().__init__(message)


class EmailAlreadyExistsError(APIBusinessException):
    """Raised when attempting to register with an email that already exists."""

    def __init__(self, email: str, context: str = "signup"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="AUTH_EMAIL_ALREADY_EXISTS",
            message="An account with this email already exists",
            context=context,
            details={"email": email},
        )


class PasswordHashingError(APIBusinessException):
    """Raised when password hashing fails."""

    def __init__(self, context: str = "signup"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="AUTH_PASSWORD_HASHING_FAILED",
            message="Failed to hash password securely",
            context=context,
        )


class TokenGenerationError(APIBusinessException):
    """Raised when token generation fails."""

    def __init__(self, context: str = "signup"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="AUTH_TOKEN_GENERATION_FAILED",
            message="Failed to generate authentication token",
            context=context,
        )


class InvalidCredentialsError(APIBusinessException):
    """Raised when login credentials are invalid."""

    def __init__(self, context: str = "login"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_INVALID_CREDENTIALS",
            message="Invalid email or password",
            context=context,
        )


class BadRequestError(APIBusinessException):
    """Raised for general bad request errors."""

    def __init__(self, message: str, context: str = "api", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BAD_REQUEST",
            message=message,
            context=context,
            details=details,
        )


class InternalServerError(APIBusinessException):
    """Raised for unexpected internal server errors."""

    def __init__(self, message: str = "An unexpected error occurred", context: str = "api", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
            message=message,
            context=context,
            details=details,
        )
