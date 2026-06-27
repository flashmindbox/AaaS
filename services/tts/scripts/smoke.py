"""Quick-and-dirty smoke test against a running TTS service.

Usage:

    python scripts/smoke.py               # hits http://127.0.0.1:8001
    python scripts/smoke.py --url X       # custom base URL (e.g. through gateway)

Writes out/demo.wav and prints latency + audio duration. Run it after
``uvicorn app.main:app`` to confirm the real model produces playable
Odia audio end-to-end.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import httpx

DEMO_LINES = [
    "ନମସ୍କାର।",
    "ମୁଁ ଓଡ଼ିଶା ସରକାରଙ୍କ ଏକ ଉଦ୍ୟୋଗ।",
    "ଆପଣଙ୍କୁ କେମିତି ସହଯୋଗ କରିପାରିବି?",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8001")
    parser.add_argument("--out", default="out/demo.wav", type=Path)
    parser.add_argument("--text", default="\n".join(DEMO_LINES))
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    with httpx.Client(base_url=args.url, timeout=60.0) as client:
        ready = client.get("/readyz")
        print(f"/readyz  -> {ready.status_code} {ready.text}")
        voices = client.get("/voices").json()
        print(f"/voices  -> {voices}")

        started = time.perf_counter()
        response = client.post("/synthesise", json={"text": args.text})
        elapsed = time.perf_counter() - started
        response.raise_for_status()
        args.out.write_bytes(response.content)

        duration = float(response.headers.get("x-audio-duration", "0"))
        rtf = elapsed / duration if duration else float("inf")
        print(
            f"/synthesise -> wrote {args.out} "
            f"({len(response.content)} B, {duration:.2f} s audio, "
            f"{elapsed:.2f} s wall, RTF={rtf:.2f})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
