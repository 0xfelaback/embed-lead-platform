from fastapi import APIRouter, Depends, status
from src.module.dtos.auth import (
    TenantRegistrationRequest,
    TenantRegistrationResponse,
    TenantLoginRequest,
    TenantLoginResponse,
    TenantLogoutResponse,
)
from src.module.services.auth import AuthService, get_AuthService

# from src.main import logger
from src.Shared.exceptions import (
    EmailAlreadyExistsError,
    PasswordHashingError,
    TokenGenerationError,
    InternalServerError,
    InvalidCredentialsError,
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


@router.post(
    "/login",
    response_model=TenantLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate a tenant",
    description="Authenticates a tenant with email and password. Returns an access token upon successful authentication.",
)
async def login(
    login_data: TenantLoginRequest,
    security_service: AuthService = Depends(get_AuthService),
):
    """
    Tenant login endpoint.

    This endpoint handles tenant authentication.

    Returns:
        TenantLoginResponse: Authenticated tenant details with access token

    Raises:
        InvalidCredentialsError: When email doesn't exist or password doesn't match
        TokenGenerationError: When token generation fails
        InternalServerError: For unexpected errors during login
    """
    try:
        tenant = await security_service.login_tenant(
            email=login_data.email,
            password=login_data.password,
        )

        access_token = security_service.generate_access_token(
            tenant_id=tenant.id, email=tenant.email
        )

        return TenantLoginResponse(
            access_token=access_token,
            tenant_id=tenant.id,
            email=tenant.email,
        )

    except InvalidCredentialsError:
        raise
    except TokenGenerationError:
        raise
    except Exception as e:
        raise InternalServerError(
            message="An unexpected error occurred during login",
            context="login",
            details={"error": str(e)},
        )


@router.post(
    "/logout",
    response_model=TenantLogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout a tenant",
    description="Logs out the current tenant. Since JWT tokens are stateless, the client should discard the token.",
)
async def logout(security_service: AuthService = Depends(get_AuthService)):
    """
    Tenant logout endpoint.

    This endpoint provides server-side confirmation and will be extended
    with token blacklisting in the future.

    Args:
        security_service: Security service for logout operations

    Returns:
        TenantLogoutResponse: Confirmation of successful logout

    Raises:
        InternalServerError: For unexpected errors during logout
    """
    try:
        security_service.logout_tenant()
        return TenantLogoutResponse()
    except Exception as e:
        raise InternalServerError(
            message="An unexpected error occurred during logout",
            context="logout",
            details={"error": str(e)},
        )
