from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

SECRET_TERMS = {
    "otp",
    "one time password",
    "pin",
    "password",
    "passcode",
    "card number",
    "cvv",
    "cvc",
    "secret code",
}

BANGLA_DIGIT_MAP = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

_SYNONYM_REPLACEMENTS = {
    "bkash": "mobile_money",
    "bikash": "mobile_money",
    "বিকাশ": "mobile_money",
    "nagad": "mobile_money",
    "নগদ": "mobile_money",
    "rocket": "mobile_money",
    "টাকা": "taka",
    "৳": " taka ",
    "ট্রান্সফার": "transfer",
    "পেমেন্ট": "payment",
    "রিফান্ড": "refund",
    "ফেরত": "refund",
    "ভুল": "wrong",
    "নাম্বার": "number",
    "নম্বর": "number",
    "প্রতারক": "scammer",
    "প্রতারণা": "fraud",
    "ফিশিং": "phishing",
    "হ্যাক": "hack",
    "ওটিপি": "otp",
    "পিন": "pin",
    "পাসওয়ার্ড": "password",
    "পাসওয়ার্ড": "password",
}

_AMOUNT_RE = re.compile(
    r"(?:(?:bdt|tk|taka|৳)\s*)?(\d{2,9}(?:[,.]\d{3})*(?:\.\d{1,2})?)\s*(?:bdt|tk|taka|টাকা)?",
    flags=re.IGNORECASE,
)

_TOKEN_RE = re.compile(r"[a-z0-9_]+|[\u0980-\u09FF]+", re.IGNORECASE)


@dataclass(frozen=True)
class PreprocessedText:
    original: str
    normalized: str
    tokens: list[str]
    amounts: list[float]
    contains_secret_terms: bool


def normalize_text(text: str) -> str:
    text = (text or "").translate(BANGLA_DIGIT_MAP)
    text = unicodedata.normalize("NFKC", text).lower()
    for source, target in _SYNONYM_REPLACEMENTS.items():
        text = text.replace(source, f" {target} ")
    text = re.sub(r"https?://\S+|www\.\S+", " url ", text)
    text = re.sub(r"[^\w\s৳\u0980-\u09FF]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)


def extract_amounts(text: str) -> list[float]:
    amounts: list[float] = []
    normalized = text.translate(BANGLA_DIGIT_MAP).replace(",", "")
    for match in _AMOUNT_RE.finditer(normalized):
        raw = match.group(1).replace(",", "")
        try:
            value = float(raw)
        except ValueError:
            continue
        # Avoid treating short phone fragments or single digits as money.
        if value >= 10:
            amounts.append(value)
    return amounts


def preprocess_text(text: str) -> PreprocessedText:
    normalized = normalize_text(text)
    tokens = tokenize(normalized)
    amounts = extract_amounts(text)
    contains_secret_terms = any(term in normalized for term in SECRET_TERMS)
    return PreprocessedText(
        original=text or "",
        normalized=normalized,
        tokens=tokens,
        amounts=amounts,
        contains_secret_terms=contains_secret_terms,
    )


def safe_sentence(text: str) -> str:
    """Remove unsafe support instructions from generated text.

    The generator in this project is template-based, but this filter protects
    against future edits accidentally adding forbidden requests.
    """
    sanitized = text
    unsafe_patterns = [
        r"\bask(?:ing)?\s+(?:for|to provide)\s+(?:otp|pin|passwords?|card numbers?)\b",
        r"\bprovide\s+(?:your\s+)?(?:otp|pin|passwords?|card numbers?|cvv)\b",
        r"\bshare\s+(?:your\s+)?(?:otp|pin|passwords?|card numbers?|cvv)\b",
        r"\bsend\s+(?:your\s+)?(?:otp|pin|passwords?|card numbers?|cvv)\b",
    ]
    for pattern in unsafe_patterns:
        sanitized = re.sub(
            pattern,
            "provide non-sensitive verification details",
            sanitized,
            flags=re.IGNORECASE,
        )
    return sanitized.strip()
