"""End-to-end test of the speak-by-voice fix.

Synthesises a 1-second 440 Hz sine in webm/Opus (exactly what the
widget's MediaRecorder emits in Chromium/Firefox), then POSTs it:
  1. directly to the STT service on :8002
  2. through the gateway on :8000 with an X-API-Key

Exits 0 if both return 200 with a non-empty transcript.
"""

from __future__ import annotations

import io
import sys
import time

import av
import httpx
import numpy as np

# Force UTF-8 stdout so Odia text doesn't hit the Windows cp-1252 codec.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

GATEWAY = "http://127.0.0.1:9000"
STT = "http://127.0.0.1:8002"
API_KEY = "aaas_live_" + "0" * 32  # the utkal-university seed key


def make_webm_blob(duration_s: float = 1.0, sr: int = 48_000) -> bytes:
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    pcm = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    buf = io.BytesIO()
    out = av.open(buf, mode="w", format="webm")
    stream = out.add_stream("libopus", rate=sr)
    stream.layout = "mono"  # type: ignore[assignment]
    frame = av.AudioFrame.from_ndarray(pcm.reshape(1, -1), format="flt", layout="mono")
    frame.sample_rate = sr
    frame.pts = 0
    for p in stream.encode(frame):
        out.mux(p)
    for p in stream.encode(None):
        out.mux(p)
    out.close()
    return buf.getvalue()


def wait_ready(url: str, timeout_s: float = 60.0) -> None:
    deadline = time.time() + timeout_s
    last_err = None
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code == 200:
                return
        except httpx.HTTPError as exc:
            last_err = exc
        time.sleep(0.5)
    raise RuntimeError(f"Service never became ready at {url}: {last_err}")


def post_direct(blob: bytes) -> dict:
    print("\n[1/2] Direct POST to STT :8002/transcribe ...")
    r = httpx.post(
        f"{STT}/transcribe",
        files={"audio": ("speech.webm", blob, "audio/webm")},
        data={"language": "or"},
        timeout=30.0,
    )
    print(f"  status: {r.status_code}")
    print(f"  body:   {r.text[:400]}")
    r.raise_for_status()
    return r.json()


def post_gateway(blob: bytes) -> dict:
    print("\n[2/2] POST through gateway :8000/stt/transcribe (with X-API-Key) ...")
    r = httpx.post(
        f"{GATEWAY}/stt/transcribe",
        files={"audio": ("speech.webm", blob, "audio/webm")},
        data={"language": "or"},
        headers={"X-API-Key": API_KEY},
        timeout=30.0,
    )
    print(f"  status: {r.status_code}")
    print(f"  body:   {r.text[:400]}")
    r.raise_for_status()
    return r.json()


def main() -> int:
    print("Waiting for STT /readyz ...")
    wait_ready(f"{STT}/readyz")
    print("  STT ready.")

    blob = make_webm_blob()
    print(f"\nSynthesised webm/Opus test blob: {len(blob)} bytes")

    direct = post_direct(blob)
    assert direct.get("text"), "direct: empty text"
    assert direct.get("language"), "direct: missing language"

    gw = post_gateway(blob)
    assert gw.get("text"), "gateway: empty text"

    print("\n-----------------------------------------")
    print("  SPEAK-BY-VOICE TEST PASSED")
    print(f"  direct   -> engine={direct.get('engine')}  text={direct.get('text')!r}")
    print(f"  gateway  -> engine={gw.get('engine')}  text={gw.get('text')!r}")
    print("-----------------------------------------")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nFAIL: {exc}")
        sys.exit(1)
