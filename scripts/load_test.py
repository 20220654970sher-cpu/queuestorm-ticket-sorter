from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import concurrent.futures
import statistics
import time
from typing import Any

import httpx

PAYLOAD = {
    "ticket_id": "LOAD-001",
    "channel": "app",
    "locale": "en",
    "message": "Payment failed but 1500 taka was deducted from my wallet",
}


def call_api(base_url: str, index: int) -> float:
    payload: dict[str, Any] = dict(PAYLOAD)
    payload["ticket_id"] = f"LOAD-{index:05d}"
    start = time.perf_counter()
    with httpx.Client(timeout=10) as client:
        response = client.post(f"{base_url}/sort-ticket", json=payload)
        response.raise_for_status()
    return (time.perf_counter() - start) * 1000


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        latencies = list(executor.map(lambda i: call_api(args.base_url, i), range(args.requests)))

    latencies_sorted = sorted(latencies)
    p95 = latencies_sorted[int(0.95 * (len(latencies_sorted) - 1))]
    print(f"requests={args.requests} workers={args.workers}")
    print(f"avg_ms={statistics.mean(latencies):.2f}")
    print(f"p95_ms={p95:.2f}")
    print(f"max_ms={max(latencies):.2f}")


if __name__ == "__main__":
    main()
