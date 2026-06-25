from __future__ import annotations

from app.models.domain import CaseType, Severity


class HumanReviewPolicy:
    def required(self, case_type: CaseType, severity: Severity, confidence: float) -> bool:
        if severity == Severity.CRITICAL:
            return True
        if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
            return True
        if confidence < 0.55:
            return True
        return False
