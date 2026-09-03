from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
import uuid
import re

class TenantRegistrationRequest(BaseModel):
    """
    DTO for tenant registration.

    This request captures the essential information needed to create a new tenant account,
    with password strength validation and email format verification.
    """

    email: EmailStr = Field(
        ...,
        description="Valid email address for the tenant account",
        examples=["tenant@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Strong password for the tenant account",
        examples=["SecureP@ssw0rd!2024"],
    )

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        """Ensure email meets format requirements."""
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Ensure password meets security requirements."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class TenantRegistrationResponse(BaseModel):
    """
    Creative DTO for successful tenant registration response.

    Returns essential account information along with authentication credentials
    and metadata about the newly created tenant.
    """

    tenant_id: uuid.UUID = Field(
        ..., description="Unique identifier for the newly created tenant"
    )
    email: EmailStr = Field(..., description="Email address of the registered tenant")
    access_token: str = Field(..., description="JWT access token for authentication")
    token_type: str = Field(
        default="bearer", description="Type of the token (always bearer)"
    )
    created_at: datetime = Field(
        ..., description="Timestamp when the tenant account was created"
    )

    class Config:
        from_attributes = True
