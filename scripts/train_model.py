from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config.settings import get_settings
from app.services.ml_classifier import TfidfLogisticTicketClassifier


def main() -> None:
    settings = get_settings()
    classifier = TfidfLogisticTicketClassifier(settings.model_path, settings.training_data_path)
    classifier.train()
    print(f"Model saved to: {settings.model_path}")


if __name__ == "__main__":
    main()
