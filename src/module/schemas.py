from typing import Any, Dict
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import (
    String,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    Index,
    Enum as SQLEnum,
    ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.Shared.Infrastructure.db_context.schema import base as Base


class WidgetType(PyEnum):
    """Enumeration of widget types."""

    SIGNUP = "signup"
    CTA = "cta"
    POPOVER = "popover"


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
        default=lambda: datetime.now(timezone.utc),
        nullable=True,
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="widgets")
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="widget", cascade="all, delete-orphan"
    )


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
