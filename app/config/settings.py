from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "QueueStorm Ticket Sorter"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", validation_alias="APP_ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    api_prefix: str = "/api/v1"

    model_path: Path = Field(
        default=Path("artifacts/ticket_classifier.joblib"),
        validation_alias="MODEL_PATH",
    )
    training_data_path: Path = Field(
        default=Path("data/training_seed.csv"),
        validation_alias="TRAINING_DATA_PATH",
    )
    confidence_threshold: float = Field(default=0.62, validation_alias="CONFIDENCE_THRESHOLD")
    enable_audit_log: bool = Field(default=True, validation_alias="APP_ENABLE_AUDIT")
    sqlite_path: Path = Field(default=Path("data/tickets.db"), validation_alias="SQLITE_PATH")
    allowed_hosts: list[str] = Field(default=["*"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
