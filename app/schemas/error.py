from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    detail: str | list[dict] | None = None
    request_id: str | None = None
