from __future__ import annotations

from app.utils.text import PreprocessedText, preprocess_text


class TicketPreprocessor:
    def preprocess(self, message: str) -> PreprocessedText:
        return preprocess_text(message)
