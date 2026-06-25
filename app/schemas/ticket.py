from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.domain import CaseType, Department, Severity


class TicketRequest(BaseModel):
    """Incoming support ticket payload.

    The message is intentionally allowed to be empty so the service can return a
    safe low-confidence classification instead of crashing during edge-case tests.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    ticket_id: str = Field(..., min_length=1, max_length=128, examples=["T-001"])
    channel: str = Field(default="unknown", min_length=1, max_length=64, examples=["app"])
    locale: str = Field(default="en", min_length=2, max_length=16, examples=["en"])
    message: str = Field(
        default="",
        max_length=5000,
        examples=["I sent 5000 taka to a wrong number"],
    )

    @field_validator("ticket_id", "channel", "locale")
    @classmethod
    def reject_blank_required_fields(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be blank")
        return value.strip()


class TicketResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: str
    case_type: CaseType
    severity: Severity
    department: Department
    agent_summary: str
    human_review_required: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
