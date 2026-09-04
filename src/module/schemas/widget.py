from typing import Any, Dict, TYPE_CHECKING
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Enum as SQLEnum,
    ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.Shared.Infrastructure.db_context.schema import base as Base

if TYPE_CHECKING:
    from src.module.schemas.submission import Submission
    from src.module.schemas.tenant import Tenant


class WidgetType(PyEnum):
    """Enumeration of widget types."""

    SIGNUP = "signup"
    CTA = "cta"
    POPOVER = "popover"


class Widget(Base):
    """
    Widget entity representing configurable UI components.

    Widgets belong to a tenant and can be of different types (signup, cta, popover).
    They contain customizable settings and can be activated/deactivated.

    Attributes:
        id: Unique identifier for the widget (primary key, indexed).
        tenant_id: Foreign key reference to the tenant that owns this widget (indexed).
        type: Widget type enum (signup, cta, popover).
        title: Display title for the widget.
        settings: JSONB field containing widget configuration (fields, submit_text, styles).
        is_active: Boolean flag indicating if the widget is active (default: true).
        created_at: Timestamp when the widget was created.
        updated_at: Timestamp when the widget was last updated.
    """

    __tablename__ = "widgets"
    __table_args__ = (Index("ix_widgets_tenant_id_id", "tenant_id", "id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[WidgetType] = mapped_column(
        SQLEnum(WidgetType, name="widget_type", create_constraint=True), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    domain_whitelist: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="widgets")
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="widget", cascade="all, delete-orphan"
    )

    def mark_widget_deleted(self):
        """Mark the widget as deleted by setting is_deleted flag and deleted_at timestamp."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
