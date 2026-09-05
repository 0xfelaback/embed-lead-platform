from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
from src.module.schemas.submission import SubmissionStatus


class SubmissionRequest(BaseModel):

    widget_id: uuid.UUID = Field(
        ..., description="ID of the widget receiving this submission"
    )
    form_data: Dict[str, Any] = Field(
        default_factory=dict, description="Form field data submitted by the user"
    )
    hp_confirm: str = Field(
        default="",
        alias="_hp_confirm",
        description="Hidden spam honeypot field (must be empty)",
    )

    @field_validator("hp_confirm")
    @classmethod
    def validate_honeypot(cls, v: str) -> str:
        """Ensure honeypot field is empty"""
        if v and v.strip():
            raise ValueError("Honeypot field not empty")
        return v


class SubmissionResponse(BaseModel):
    id: uuid.UUID = Field(..., description="Submission ID")
    widget_id: uuid.UUID = Field(..., description="ID of the widget that received this submission")
    tenant_id: uuid.UUID = Field(..., description="ID of the tenant owning the widget")
    payload: Dict[str, Any] = Field(..., description="Submitted form data")
    client_ip: str = Field(..., description="IP address of the submitting client")
    geo_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Geolocation data for the client IP"
    )
    user_agent: str = Field(..., description="User agent string from the client")
    origin: str = Field(..., description="Origin header from the client's request")
    status: SubmissionStatus = Field(..., description="Submission status")
    created_at: datetime = Field(..., description="Timestamp when the submission was created")

    class Config:
        from_attributes = True
