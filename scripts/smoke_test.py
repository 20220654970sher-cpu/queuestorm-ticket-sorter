from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json

import httpx

BASE_URL = "http://127.0.0.1:8000"

payloads = [
    {
        "ticket_id": "T-001",
        "channel": "app",
        "locale": "en",
        "message": "I sent 5000 taka to a wrong number this morning, please help me get it back",
    },
    {
        "ticket_id": "T-002",
        "channel": "sms",
        "locale": "bn",
        "message": "একজন প্রতারক আমার ওটিপি নিয়ে টাকা নিয়েছে",
    },
]


def main() -> None:
    with httpx.Client(timeout=10) as client:
        print(client.get(f"{BASE_URL}/health").json())
        for payload in payloads:
            response = client.post(f"{BASE_URL}/sort-ticket", json=payload)
            response.raise_for_status()
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
