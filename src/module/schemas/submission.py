from __future__ import annotations
from typing import Any, Dict, TYPE_CHECKING
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.Shared.Infrastructure.db_context.schema import base as Base

if TYPE_CHECKING:
    from src.module.schemas.tenant import Tenant
    from src.module.schemas.widget import Widget


class Submission(Base):
    """
    Submission entity representing form submissions from widgets.

    Submissions are linked to both a widget and a tenant, containing the payload
    data along with metadata like client IP, geolocation, and user agent.

    Attributes:
        id: Unique identifier for the submission (primary key, indexed).
        widget_id: Foreign key reference to the widget that received this submission (indexed).
        tenant_id: Foreign key reference to the tenant that owns the widget (indexed).
        payload: JSONB field containing the submission data.
        client_ip: IP address of the client submitting the form.
        geo_data: JSONB field containing geolocation data (nullable).
        user_agent: User agent string from the client's browser.
        created_at: Timestamp when the submission was created (indexed).
    """

    __tablename__ = "submissions"
    __table_args__ = (
        Index(
            "ix_submissions_tenant_id_widget_id_created_at",
            "tenant_id",
            "widget_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4
    )
    widget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("widgets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    client_ip: Mapped[str] = mapped_column(INET, nullable=False)
    geo_data: Mapped[Dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    user_agent: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    widget: Mapped["Widget"] = relationship("Widget", back_populates="submissions")
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="submissions")
