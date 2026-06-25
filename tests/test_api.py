from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_wrong_transfer() -> None:
    response = client.post(
        "/sort-ticket",
        json={
            "ticket_id": "T-001",
            "channel": "app",
            "locale": "en",
            "message": "I sent 5000 taka to a wrong number this morning",
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert data["case_type"] == "wrong_transfer"
    assert data["department"] == "dispute_resolution"
    assert data["severity"] in {"high", "critical"}
    assert data["human_review_required"] is False or data["severity"] == "critical"


def test_phishing_requires_review() -> None:
    response = client.post(
        "/sort-ticket",
        json={
            "ticket_id": "T-002",
            "channel": "sms",
            "locale": "en",
            "message": "Someone called and asked for my OTP, now my account is hacked",
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert data["case_type"] == "phishing_or_social_engineering"
    assert data["department"] == "fraud_risk"
    assert data["human_review_required"] is True
    assert data["severity"] == "critical"


def test_empty_message_safe_low_confidence() -> None:
    response = client.post(
        "/sort-ticket",
        json={"ticket_id": "T-003", "channel": "app", "locale": "en", "message": ""},
    )
    data = response.json()
    assert response.status_code == 200
    assert data["case_type"] == "other"
    assert data["confidence"] < 0.55
    assert data["human_review_required"] is True


def test_bangla_mixed_language() -> None:
    response = client.post(
        "/sort-ticket",
        json={
            "ticket_id": "T-004",
            "channel": "app",
            "locale": "bn",
            "message": "ভুল number এ ২০০০ টাকা পাঠিয়েছি help me",
        },
    )
    data = response.json()
    assert response.status_code == 200
    assert data["case_type"] == "wrong_transfer"


def test_invalid_json_validation_error() -> None:
    response = client.post(
        "/sort-ticket",
        content="not-json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"
