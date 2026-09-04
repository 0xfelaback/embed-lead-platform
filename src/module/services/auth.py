from uuid import UUID
from datetime import datetime, timedelta, timezone
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from src.Shared.Infrastructure.db_context.config import get_db
from src.Shared.Infrastructure.db_context.context import settings
from jwt import PyJWT
from src.main import logger
from src.module.schemas.tenant import Tenant
from src.module.repositories.tenant import TenantRepository
from typing import Any
from jwt.exceptions import PyJWTError
from src.Shared.exceptions import (
    EmailAlreadyExistsError,
    PasswordHashingError,
    TokenGenerationError,
    InvalidCredentialsError,
)
from jwt import decode  # type: ignore
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

security = HTTPBearer()


class AuthService:
    """
    Service handling security-related business logic for tenant authentication.

    This service encapsulates password hashing, JWT token generation, and tenant
    registration workflows with proper error handling and security best practices.
    """

    def __init__(
        self,
        session: AsyncSession,
        jwt_secret: str = settings.JWT_SECRET,
    ):
        """
        Initialize the security service.

        Args:
            session: Database session for async operations
            jwt_secret: Secret key for JWT token signing
        """
        self.session = session
        self.tenant_repository = TenantRepository(session)
        self.jwt_secret = jwt_secret
        self.password_hasher = PasswordHash((Argon2Hasher(),))
        self.jwt = PyJWT()

    async def get_current_tenant(
        self, credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
    ) -> Tenant:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            token = credentials.credentials
            payload: dict[str, Any] = decode(
                token, settings.JWT_SECRET, algorithms=["HS256"]
            )
            email: str | None = payload.get("email")
            if email is None:
                raise credentials_exception
        except InvalidTokenError:
            raise credentials_exception

        tenant = await self.tenant_repository.get_by_email(email)
        if tenant is None:
            raise credentials_exception
        return tenant

    def hash_password(self, password: str) -> str:
        try:
            hashed = self.password_hasher.hash(password)
            logger.info("Password hashed successfully")
            return hashed
        except Exception as e:
            logger.error(f"Password hashing failed: {str(e)}")
            raise PasswordHashingError(context="password_hashing")

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Returns:
            True if password matches, False otherwise
        """
        try:
            result = self.password_hasher.verify(password, hashed_password)
            logger.info("Password verification completed")
            return result
        except Exception as e:
            logger.error(f"Password verification failed: {str(e)}")
            return False

    def generate_access_token(self, tenant_id: UUID, email: str) -> str:
        """
        Generate a JWT access token for a tenant.

        Args:
            tenant_id
            email: Email address of the tenant

        Returns:
            JWT access token string
        """
        try:
            now = datetime.now(timezone.utc)
            expiry = now + timedelta(hours=24)

            payload: dict[str, Any] = {
                "sub": str(tenant_id),
                "email": email,
                "IssuedAt": now.timestamp(),
                "expires_delta": expiry.timestamp(),
            }

            encoded_jwt: str = (
                self.jwt.encode(  # pyright: ignore[reportUnknownMemberType]
                    payload, self.jwt_secret, algorithm="HS256"
                )
            )
            logger.info(f"Access token generated for tenant {tenant_id}")
            return encoded_jwt
        except PyJWTError as e:
            logger.error(f"JWT encoding failed: {str(e)}")
            raise TokenGenerationError(context="token_generation")
        except Exception as e:
            logger.error(f"Token generation failed: {str(e)}")
            raise TokenGenerationError(context="token_generation")

    async def register_tenant(self, email: str, password: str) -> Tenant:
        """
        Register a new tenant with email and password.

        Args:
            email: Email address for the tenant
            password: Plain text password (will be hashed)

        Returns:
            Created Tenant entity
        """
        key_hash = self.hash_password(password)
        new_tenant = await self.tenant_repository.create(email, key_hash)

        if not new_tenant:
            logger.warning(f"Registration failed: Email already exists - {email}")
            raise EmailAlreadyExistsError(email=email, context="signup")

        logger.info(f"New tenant registered successfully: {email}")
        return new_tenant

    async def login_tenant(self, email: str, password: str) -> Tenant:
        """
        Authenticate a tenant with email and password.

        Args:
            email: Email address for the tenant
            password: Plain text password to verify

        Returns:
            Authenticated Tenant entity

        Raises:
            InvalidCredentialsError: If email doesn't exist or password doesn't match
        """
        tenant = await self.tenant_repository.get_by_email(email)

        if not tenant:
            logger.warning(f"Login failed: Tenant not found - {email}")
            raise InvalidCredentialsError(context="login")

        if not self.verify_password(password, tenant.key_hash):
            logger.warning(f"Login failed: Invalid password - {email}")
            raise InvalidCredentialsError(context="login")

        logger.info(f"Tenant logged in successfully: {email}")
        return tenant

    def logout_tenant(self) -> None:
        """
        Logout a tenant.

        Note: For server-side logout, implement the yet to be implemented token blacklisting.
        """
        logger.info("Tenant logout requested")


def get_AuthService(
    session: AsyncSession = Depends(get_db),
) -> AuthService:
    return AuthService(session=session)
