from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import FunctionTransformer

from app.models.domain import CaseType, Severity
from app.utils.text import normalize_text

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MLPrediction:
    case_type: CaseType
    case_confidence: float
    severity: Severity
    severity_confidence: float


def _identity(values: list[str]) -> list[str]:
    return values


class TfidfLogisticTicketClassifier:
    """Lightweight CPU-friendly model with word and character n-grams.

    Character n-grams make the model more robust to common typo forms like
    `paymnt faild`, `refnd`, and mixed Bangla-English transliteration.
    """

    def __init__(self, model_path: Path, training_data_path: Path) -> None:
        self.model_path = model_path
        self.training_data_path = training_data_path
        self.case_model: Pipeline | None = None
        self.severity_model: Pipeline | None = None

    def load_or_train(self) -> None:
        if self.model_path.exists():
            payload = joblib.load(self.model_path)
            self.case_model = payload["case_model"]
            self.severity_model = payload["severity_model"]
            logger.info("Loaded classifier artifact from %s", self.model_path)
            return
        self.train()

    def train(self) -> None:
        if not self.training_data_path.exists():
            raise FileNotFoundError(f"Training data not found: {self.training_data_path}")
        df = pd.read_csv(self.training_data_path)
        required = {"message", "case_type", "severity"}
        missing = required.difference(df.columns)
        if missing:
            raise ValueError(f"Training data missing columns: {sorted(missing)}")

        x = df["message"].fillna("").map(normalize_text).tolist()
        y_case = df["case_type"].tolist()
        y_severity = df["severity"].tolist()

        self.case_model = self._build_pipeline(class_weight="balanced")
        self.severity_model = self._build_pipeline(class_weight="balanced")
        self.case_model.fit(x, y_case)
        self.severity_model.fit(x, y_severity)

        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"case_model": self.case_model, "severity_model": self.severity_model},
            self.model_path,
        )
        logger.info("Trained and saved classifier artifact to %s", self.model_path)

    def predict(self, normalized_message: str) -> MLPrediction:
        if self.case_model is None or self.severity_model is None:
            self.load_or_train()

        assert self.case_model is not None
        assert self.severity_model is not None
        text = normalize_text(normalized_message)
        case_probs = self.case_model.predict_proba([text])[0]
        case_labels = list(self.case_model.classes_)
        severity_probs = self.severity_model.predict_proba([text])[0]
        severity_labels = list(self.severity_model.classes_)

        case_idx = int(case_probs.argmax())
        severity_idx = int(severity_probs.argmax())
        return MLPrediction(
            case_type=CaseType(case_labels[case_idx]),
            case_confidence=float(case_probs[case_idx]),
            severity=Severity(severity_labels[severity_idx]),
            severity_confidence=float(severity_probs[severity_idx]),
        )

    def _build_pipeline(self, class_weight: str | dict | None = None) -> Pipeline:
        features = FeatureUnion(
            [
                (
                    "word_tfidf",
                    TfidfVectorizer(
                        analyzer="word",
                        ngram_range=(1, 2),
                        min_df=1,
                        sublinear_tf=True,
                    ),
                ),
                (
                    "char_tfidf",
                    TfidfVectorizer(
                        analyzer="char_wb",
                        ngram_range=(3, 5),
                        min_df=1,
                        sublinear_tf=True,
                    ),
                ),
            ]
        )
        return Pipeline(
            [
                ("identity", FunctionTransformer(_identity, validate=False)),
                ("features", features),
                (
                    "clf",
                    OneVsRestClassifier(
                        LogisticRegression(
                            max_iter=600,
                            solver="liblinear",
                            class_weight=class_weight,
                            random_state=42,
                        )
                    ),
                ),
            ]
        )
