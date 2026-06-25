from __future__ import annotations

from collections import Counter

from app.utils.text import PreprocessedText

DOMAIN_TERMS = {
    "wrong",
    "number",
    "recipient",
    "payment",
    "failed",
    "deducted",
    "refund",
    "cashback",
    "fraud",
    "scam",
    "phishing",
    "otp",
    "pin",
    "password",
    "hacked",
    "unauthorized",
    "transfer",
    "merchant",
    "taka",
    "mobile_money",
}

STOPWORDS = {
    "i",
    "me",
    "my",
    "the",
    "a",
    "an",
    "to",
    "for",
    "from",
    "and",
    "or",
    "but",
    "please",
    "help",
    "need",
    "want",
    "this",
    "that",
    "is",
    "was",
    "are",
    "be",
    "it",
    "in",
    "on",
    "of",
}


class KeywordExtractor:
    """Small deterministic keyword extractor for explainability and logging."""

    def extract(self, preprocessed: PreprocessedText, max_keywords: int = 8) -> list[str]:
        weighted_terms: list[str] = []
        for token in preprocessed.tokens:
            if len(token) < 3 or token in STOPWORDS:
                continue
            weight = 3 if token in DOMAIN_TERMS else 1
            weighted_terms.extend([token] * weight)
        keywords = [term for term, _ in Counter(weighted_terms).most_common(max_keywords)]
        if preprocessed.amounts:
            keywords.append(f"amount:{max(preprocessed.amounts):.0f}")
        return keywords[:max_keywords]
