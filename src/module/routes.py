from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.Shared.Infrastructure.db_context.config import get_db
from src.module.dtos import (
    TenantRegistrationRequest,
    TenantRegistrationResponse,
)
from src.module.service import AuthService, get_AuthService

# from src.main import logger
from src.Shared.exceptions import (
    EmailAlreadyExistsError,
    PasswordHashingError,
    TokenGenerationError,
    InternalServerError,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=TenantRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new tenant",
    description="Creates a new tenant account with email and password. Returns an access token upon successful registration.",
)
async def signup(
    registration_data: TenantRegistrationRequest,
    session: AsyncSession = Depends(get_db),
    security_service: AuthService = Depends(get_AuthService),
):
    """
    Tenant registration endpoint.

    This endpoint handles new tenant registration with the following workflow:
    1. Validates the registration request (email format, password strength)
    2. Checks if the email is already registered
    3. Hashes the password using Argon2
    4. Creates the tenant record in the database
    5. Generates a JWT access token
    6. Returns the tenant information and access token

    Args:
        registration_data: Tenant registration details including email and password
        session: Database session for async operations
        security_service: Security service for password hashing and token generation

    Returns:
        TenantRegistrationResponse: Created tenant details with access token

    Raises:
        EmailAlreadyExistsError: When the email is already registered
        PasswordHashingError: When password hashing fails
        TokenGenerationError: When token generation fails
        InternalServerError: For unexpected errors during registration
    """
    try:
        tenant = await security_service.register_tenant(
            email=registration_data.email,
            password=registration_data.password,
        )

        access_token = security_service.generate_access_token(
            tenant_id=tenant.id, email=tenant.email
        )

        return TenantRegistrationResponse(
            tenant_id=tenant.id,
            email=tenant.email,
            access_token=access_token,
            token_type="bearer",
            created_at=tenant.created_at,
        )

    except EmailAlreadyExistsError:
        raise
    except PasswordHashingError:
        raise
    except TokenGenerationError:
        raise
    except ValueError as e:
        raise InternalServerError(
            message=str(e), context="signup", details={"error_type": "ValueError"}
        )
    except Exception as e:
        raise InternalServerError(
            message="An unexpected error occurred during registration",
            context="signup",
            details={"error": str(e)},
        )
