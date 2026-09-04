from enum import Enum
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    HttpUrl,
    model_validator,
)
from typing import Optional, List, Dict, Any
import uuid
import re
from datetime import datetime

from src.module.schemas.widget import WidgetType


class InputType(Enum):
    TEXT = "text"
    EMAIL = "email"
    NUMBER = "number"
    TEXTAREA = "textarea"
    SELECT = "select"
    CHECKBOX = "checkbox"


class WidgetFieldDefinition(BaseModel):
    """
    Schema for defining a single field in widget settings.

    For 'select' field type: options array is required and defines the dropdown choices.
    For 'checkbox' field type: options array is required and defines the available checkbox options.
    For other field types (text, email, number, textarea): options array is ignored.
    """

    name: str = Field(..., description="Field name/identifier")
    type: InputType = Field(..., description="Field type")
    label: str = Field(..., description="Display label for the field")
    required: bool = Field(default=False, description="Whether the field is required")
    placeholder: Optional[str] = Field(None, description="Placeholder text")
    options: Optional[List[str]] = Field(
        None,
        description="Required for 'select' and 'checkbox' types. Array of string options (e.g., ['Option A', 'Option B']). Ignored for other types.",
    )


class WidgetSettings(BaseModel):
    """Schema for widget settings configuration."""

    submit_button_text: str = Field(
        default="Submit", description="Text for submit button"
    )
    fields: List[WidgetFieldDefinition] = Field(
        default_factory=list[WidgetFieldDefinition],
        description="Form field definitions",
    )
    success_message: Optional[str] = Field(
        None, description="Message shown after successful submission"
    )
    redirect_url: Optional[HttpUrl] = Field(
        None, description="URL to redirect after submission"
    )


class WidgetCreateRequest(BaseModel):
    """
    DTO for creating a new widget.

    This request captures the configuration needed to create a widget
    with proper validation for types and settings.
    """

    type: WidgetType = Field(..., description="Widget type (signup, cta, or popover)")
    title: str = Field(..., min_length=1, max_length=255, description="Widget title")
    settings: WidgetSettings = Field(..., description="Widget configuration settings")
    domain_whitelist: List[str] = Field(
        default_factory=list,
        description="Valid hostnames/origins (e.g., ['example.com']). Empty list = no domains allowed.",
    )

    @field_validator("title")
    @classmethod
    def clean_and_validate_title(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Title cannot be empty or consist only of whitespace.")
        return cleaned

    @field_validator("domain_whitelist")
    @classmethod
    def validate_domains(cls, v: List[str]) -> List[str]:
        """Validate that provided domains match a valid hostname or regex pattern."""
        if not v:
            return v

        # regex for valid domains, allows subdomains and localhost, excludes protocol/paths.
        domain_regex = re.compile(
            r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$|^localhost$"
        )

        cleaned_domains: List[str] = []
        for domain in v:
            cleaned = domain.strip().lower()
            cleaned = re.sub(r"^https?://", "", cleaned).split("/")[0]

            if not domain_regex.match(cleaned):
                raise ValueError(
                    f"Invalid domain format: '{domain}'. Expected clean hostname like 'example.com'."
                )
            cleaned_domains.append(cleaned)

        return list(set(cleaned_domains))  # Deduplicate domains

    @model_validator(mode="after")
    def validate_settings_match_type(self) -> "WidgetCreateRequest":
        """
        Cross-field validation. Ensures the 'settings' object matches the 'type'.
        (e.g., If type is 'signup', ensure fields are configured properly).
        """
        # Convert settings to dict for checking
        settings_dict: Dict[str, Any] = self.settings.model_dump(mode="json")

        if self.type == WidgetType.SIGNUP:
            if not settings_dict.get("fields"):
                raise ValueError(
                    "Widgets of type 'signup' must have at least one field configured in settings."
                )

            field_names = [
                field.get("name") for field in settings_dict.get("fields", [])
            ]
            if "email" not in field_names:
                raise ValueError(
                    "Widgets of type 'signup' must include an 'email' field."
                )

        elif self.type == WidgetType.CTA:
            if not settings_dict.get("submit_button_text"):
                raise ValueError(
                    "Widgets of type 'cta' must have submit_button_text configured."
                )

        elif self.type == WidgetType.POPOVER:
            if not settings_dict.get("fields"):
                raise ValueError(
                    "Widgets of type 'popover' must have at least one field configured in settings."
                )

        return self


class WidgetUpdateRequest(BaseModel):
    """
    DTO for updating an existing widget.

    This request captures partial updates for a widget with proper validation.
    All fields are optional to support partial updates.
    """

    title: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Widget title"
    )
    is_active: Optional[bool] = Field(None, description="Whether widget is active")
    domain_whitelist: Optional[List[str]] = Field(
        None,
        description="Valid hostnames/origins (e.g., ['example.com']). Empty list = no domains allowed. Replaces existing array.",
    )
    settings: Optional[WidgetSettings] = Field(
        None, description="Widget configuration settings (full replacement)"
    )

    @field_validator("title")
    @classmethod
    def clean_and_validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Title cannot be empty or consist only of whitespace.")
        return cleaned

    @field_validator("domain_whitelist")
    @classmethod
    def validate_domains(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate that provided domains match a valid hostname or regex pattern."""
        if not v:
            return v

        domain_regex = re.compile(
            r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$|^localhost$"
        )

        cleaned_domains: List[str] = []
        for domain in v:
            cleaned = domain.strip().lower()
            cleaned = re.sub(r"^https?://", "", cleaned).split("/")[0]

            if not domain_regex.match(cleaned):
                raise ValueError(
                    f"Invalid domain format: '{domain}'. Expected clean hostname like 'example.com'."
                )
            cleaned_domains.append(cleaned)

        return list(set(cleaned_domains))  # Deduplicate domains


class WidgetCreateResponse(BaseModel):

    id: uuid.UUID = Field(..., description="Widget ID")
    tenant_id: uuid.UUID = Field(..., description="Tenant ID")
    type: str = Field(..., description="Widget type")
    title: str = Field(..., description="Widget title")
    settings: Dict[str, Any] = Field(..., description="Widget settings")
    embed_snippet: str = Field(..., description="Embed script snippet")
    is_active: bool = Field(..., description="Whether widget is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(
        default=None, description="Last update timestamp"
    )

    class Config:
        from_attributes = True


class WidgetListItem(BaseModel):
    """Simplified widget representation for list views."""

    id: uuid.UUID = Field(..., description="Widget ID")
    type: str = Field(..., description="Widget type")
    title: str = Field(..., description="Widget title")
    is_active: bool = Field(..., description="Whether widget is active")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class PaginationInfo(BaseModel):
    """Pagination metadata."""

    current_page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_records: int = Field(..., description="Total number of records")
    total_pages: int = Field(..., description="Total number of pages")


class WidgetListResponse(BaseModel):
    """Response for widget list endpoint with pagination."""

    data: List[WidgetListItem] = Field(..., description="List of widgets")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")


class SingleWidgetListItemResponse(WidgetListItem):
    tenant_id: uuid.UUID = Field(..., description="Tenant ID")
    domain_whitelist: List[str] = Field(
        ..., description="List of allowed domains where the widget can be embedded"
    )
    settings: dict[str, Any] = Field(
        ..., description="Configuration and UI settings specific to the widget type"
    )
    embed_snippet: str = Field(
        ..., description="HTML script tag used to embed the widget on external sites"
    )
    updated_at: Optional[datetime] = Field(
        default=None, description="Updated At timestamp"
    )
