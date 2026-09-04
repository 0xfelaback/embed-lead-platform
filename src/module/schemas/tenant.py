import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String,
    DateTime,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.Shared.Infrastructure.db_context.schema import base as Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.module.schemas.submission import Submission
    from src.module.schemas.widget import Widget


class Tenant(Base):
    """
    Tenant entity representing a customer account.

    Tenants are the top-level entities that own widgets and receive submissions.
    Each tenant has a unique email and a key hash for authentication.

    Attributes:
        id: Unique identifier for the tenant (primary key, indexed).
        email: Unique email address for the tenant.
        key_hash: Hashed key for authentication purposes.
        created_at: Timestamp when the tenant was created.
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    widgets: Mapped[list["Widget"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
