from __future__ import annotations

from app.models.domain import CaseType, Severity
from app.utils.text import PreprocessedText, safe_sentence


class AgentSummaryGenerator:
    def generate(
        self,
        preprocessed: PreprocessedText,
        case_type: CaseType,
        severity: Severity,
    ) -> str:
        amount = max(preprocessed.amounts, default=0.0)
        amount_fragment = f" involving approximately {amount:,.0f} BDT" if amount else ""

        templates = {
            CaseType.WRONG_TRANSFER: (
                "Customer reports sending money to an incorrect recipient"
                f"{amount_fragment} and requests recovery assistance."
            ),
            CaseType.PAYMENT_FAILED: (
                "Customer reports a failed or incomplete payment"
                f"{amount_fragment} and needs transaction status verification."
            ),
            CaseType.REFUND_REQUEST: (
                "Customer requests a refund or reversal"
                f"{amount_fragment} and needs follow-up on eligibility or processing status."
            ),
            CaseType.PHISHING_OR_SOCIAL_ENGINEERING: (
                "Customer reports a possible fraud, phishing, account compromise, "
                "or social engineering incident; the case needs secure fraud-risk review."
            ),
            CaseType.OTHER: (
                "Customer submitted a support message that does not clearly match "
                "payment failure, refund, wrong transfer, or phishing categories."
            ),
        }
        summary = templates[case_type]
        if severity == Severity.CRITICAL:
            summary += " Treat as critical due to potential financial or account safety impact."
        return safe_sentence(summary)
