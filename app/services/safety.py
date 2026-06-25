from __future__ import annotations

from app.utils.text import SECRET_TERMS, safe_sentence


class SummarySafetyFilter:
    def validate(self, summary: str) -> str:
        sanitized = safe_sentence(summary)
        lowered = sanitized.lower()
        forbidden_action_terms = ("ask for", "provide your", "share your", "send your")
        has_unsafe_action = any(action in lowered for action in forbidden_action_terms)
        has_secret_term = any(term in lowered for term in SECRET_TERMS)
        if has_unsafe_action and has_secret_term:
            return (
                "Customer support case summary generated. "
                "Sensitive credential collection is prohibited."
            )
        return sanitized
