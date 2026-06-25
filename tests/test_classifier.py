from __future__ import annotations

from app.config.settings import get_settings
from app.models.domain import CaseType, Severity
from app.services.classifier import TicketSortingService
from app.schemas.ticket import TicketRequest


def make_service() -> TicketSortingService:
    settings = get_settings()
    service = TicketSortingService(settings)
    service.warmup()
    return service


def test_payment_failed_classification() -> None:
    service = make_service()
    response = service.sort(
        TicketRequest(
            ticket_id="U-001",
            channel="app",
            locale="en",
            message="Payment failed but my wallet balance was deducted",
        )
    )
    assert response.case_type == CaseType.PAYMENT_FAILED
    assert response.department.value == "payments_ops"


def test_critical_human_review_rule() -> None:
    service = make_service()
    response = service.sort(
        TicketRequest(
            ticket_id="U-002",
            channel="app",
            locale="en",
            message="I clicked a fake link and my account is hacked",
        )
    )
    assert response.severity == Severity.CRITICAL
    assert response.human_review_required is True


def test_summary_never_requests_credentials() -> None:
    service = make_service()
    response = service.sort(
        TicketRequest(
            ticket_id="U-003",
            channel="app",
            locale="en",
            message="Someone asked for my OTP and PIN",
        )
    )
    summary = response.agent_summary.lower()
    assert "ask for otp" not in summary
    assert "provide your otp" not in summary
    assert "password" not in summary
    assert "card number" not in summary
