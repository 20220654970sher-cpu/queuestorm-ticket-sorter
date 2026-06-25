from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any


class SQLiteAuditLog:
    """Tiny local audit store for demo/prototype traceability.

    In production, replace this with PostgreSQL or an event stream. The service
    is deliberately optional and failure-isolated so classification never fails
    because of local disk problems.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ticket_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    response_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS "
                "idx_ticket_audit_ticket_id ON ticket_audit(ticket_id)"
            )
            conn.commit()
        self._initialized = True

    def record(
        self,
        ticket_id: str,
        request_payload: dict[str, Any],
        response_payload: dict[str, Any],
    ) -> None:
        self.initialize()
        with self._lock:
            with closing(sqlite3.connect(self.path)) as conn:
                conn.execute(
                    """
                    INSERT INTO ticket_audit(ticket_id, created_at, request_json, response_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        ticket_id,
                        datetime.now(UTC).isoformat(),
                        json.dumps(request_payload, ensure_ascii=False),
                        json.dumps(response_payload, ensure_ascii=False),
                    ),
                )
                conn.commit()
