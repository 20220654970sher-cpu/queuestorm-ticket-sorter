from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable

from app.models.domain import CASE_TO_DEPARTMENT, CaseType, Department, Severity
from app.utils.text import PreprocessedText


def _has_any(text: str, phrases: Iterable[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _fuzzy_contains(tokens: list[str], keywords: Iterable[str], threshold: float = 0.82) -> bool:
    for token in tokens:
        if len(token) < 4:
            continue
        for keyword in keywords:
            if SequenceMatcher(None, token, keyword).ratio() >= threshold:
                return True
    return False


@dataclass(frozen=True)
class RulePrediction:
    case_type: CaseType
    severity: Severity
    department: Department
    case_score: float
    severity_score: float
    reasons: list[str]


class KeywordRuleEngine:
    """High-precision deterministic rules for fintech support tickets."""

    PHISHING_PHRASES = (
        "phishing",
        "fraud",
        "scam",
        "scammer",
        "hack",
        "hacked",
        "account hacked",
        "fake link",
        "suspicious link",
        "login link",
        "unknown link",
        "otp",
        "pin",
        "password",
        "pretending",
        "impersonat",
        "social engineering",
        "unauthorized",
        "unauthorised",
        "not me",
        "without my permission",
        "someone called",
        "agent called",
        "asked for code",
        "asked me code",
        "asked me otp",
        "তাকা",  # harmless fuzzy catch for some noisy Bangla inputs
    )
    WRONG_TRANSFER_PHRASES = (
        "wrong number",
        "wrong recipient",
        "incorrect recipient",
        "incorrect number",
        "mistaken number",
        "sent to wrong",
        "send to wrong",
        "transferred to wrong",
        "wrong account",
        "mistake transfer",
        "mistakenly sent",
        "accidentally sent",
        "ভুল number",
        "wrong mobile_money",
    )
    PAYMENT_FAILED_PHRASES = (
        "payment failed",
        "transaction failed",
        "cash out failed",
        "send money failed",
        "sent but failed",
        "sent taka but failed",
        "sent money but failed",
        "money deducted but failed",
        "taka deducted",
        "not received",
        "top up failed",
        "recharge failed",
        "bill payment failed",
        "debited but",
        "deducted but",
        "charged but",
        "money deducted",
        "balance deducted",
        "payment not completed",
        "merchant did not receive",
        "pending transaction",
        "পেমেন্ট failed",
    )
    REFUND_PHRASES = (
        "refund",
        "refund request",
        "refund chai",
        "ferot",
        "return my money",
        "money back",
        "cashback missing",
        "cancel order",
        "order cancelled",
        "merchant refund",
        "reverse payment",
        "chargeback",
        "রিফান্ড",
    )
    URGENCY_PHRASES = (
        "urgent",
        "immediately",
        "asap",
        "emergency",
        "right now",
        "can't access",
        "cannot access",
        "blocked",
        "locked",
        "all money",
        "life savings",
    )

    def predict(self, preprocessed: PreprocessedText) -> RulePrediction:
        text = preprocessed.normalized
        tokens = preprocessed.tokens
        reasons: list[str] = []
        scores = {
            CaseType.PHISHING_OR_SOCIAL_ENGINEERING: 0.0,
            CaseType.WRONG_TRANSFER: 0.0,
            CaseType.PAYMENT_FAILED: 0.0,
            CaseType.REFUND_REQUEST: 0.0,
            CaseType.OTHER: 0.15,
        }

        if _has_any(text, self.PHISHING_PHRASES) or preprocessed.contains_secret_terms:
            scores[CaseType.PHISHING_OR_SOCIAL_ENGINEERING] += 0.88
            reasons.append("phishing/fraud/security keywords detected")
        wrong_target = "number" in tokens or "recipient" in tokens or "account" in tokens
        if _has_any(text, self.WRONG_TRANSFER_PHRASES) or ("wrong" in tokens and wrong_target):
            scores[CaseType.WRONG_TRANSFER] += 0.88
            reasons.append("wrong recipient transfer pattern detected")
        failed_status = "failed" in tokens or "pending" in tokens or "not received" in text
        payment_target = "payment" in tokens or "transaction" in tokens
        money_movement_target = any(
            token in tokens for token in ("sent", "send", "money", "taka", "mobile_money")
        )
        if (
            _has_any(text, self.PAYMENT_FAILED_PHRASES)
            or (failed_status and payment_target)
            or (failed_status and money_movement_target)
        ):
            scores[CaseType.PAYMENT_FAILED] += 0.86
            reasons.append("payment failure pattern detected")
        if _has_any(text, self.REFUND_PHRASES) or _fuzzy_contains(tokens, ["refund", "cashback"]):
            scores[CaseType.REFUND_REQUEST] += 0.82
            reasons.append("refund request pattern detected")

        # Multi-complaint tie-breakers: security risk wins, then money movement disputes.
        case_priority = [
            CaseType.PHISHING_OR_SOCIAL_ENGINEERING,
            CaseType.WRONG_TRANSFER,
            CaseType.PAYMENT_FAILED,
            CaseType.REFUND_REQUEST,
            CaseType.OTHER,
        ]
        case_type = max(case_priority, key=lambda case: (scores[case], -case_priority.index(case)))
        case_score = min(scores[case_type], 0.98)

        severity, severity_score = self._predict_severity(preprocessed, case_type, reasons)
        department = self._department_for(case_type, text)
        return RulePrediction(case_type, severity, department, case_score, severity_score, reasons)

    def _predict_severity(
        self,
        preprocessed: PreprocessedText,
        case_type: CaseType,
        reasons: list[str],
    ) -> tuple[Severity, float]:
        text = preprocessed.normalized
        max_amount = max(preprocessed.amounts, default=0.0)
        urgent = _has_any(text, self.URGENCY_PHRASES)

        if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
            severe_security_terms = (
                "hacked",
                "unauthorized",
                "without my permission",
                "otp",
                "pin",
                "password",
                "all money",
            )
            if _has_any(text, severe_security_terms):
                reasons.append("security-sensitive phishing/hijack indicators detected")
                return Severity.CRITICAL, 0.95
            return Severity.HIGH, 0.89

        if max_amount >= 50000:
            reasons.append("very large monetary amount detected")
            return Severity.CRITICAL, 0.9
        if case_type == CaseType.WRONG_TRANSFER:
            if max_amount >= 1000 or urgent:
                return Severity.HIGH, 0.86
            return Severity.MEDIUM, 0.78
        if case_type == CaseType.PAYMENT_FAILED:
            if max_amount >= 10000 or urgent:
                return Severity.HIGH, 0.82
            return Severity.MEDIUM, 0.76
        if case_type == CaseType.REFUND_REQUEST:
            if max_amount >= 20000:
                return Severity.HIGH, 0.78
            return Severity.MEDIUM, 0.72
        if not preprocessed.normalized:
            reasons.append("empty message")
            return Severity.LOW, 0.4
        return Severity.LOW, 0.56

    def _department_for(self, case_type: CaseType, text: str) -> Department:
        if case_type == CaseType.REFUND_REQUEST and any(
            phrase in text
            for phrase in ("chargeback", "merchant dispute", "unauthorized", "wrong merchant")
        ):
            return Department.DISPUTE_RESOLUTION
        return CASE_TO_DEPARTMENT[case_type]
