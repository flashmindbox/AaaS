"""Entry-point for the PyInstaller-bundled gateway.

Boots uvicorn on the configured port and serves:

- ``POST /tts/synthesise``, ``/stt/*``, ``/admin/*`` (proxied to upstream)
- ``GET  /widget.js``       (static widget JS for drop-in embed)
- ``GET  /demo/<site>/``    (Jajpur mock sites)
- ``GET  /healthz``, ``/readyz``, ``/version``

Defaults to ``0.0.0.0:8000`` so other devices on the same LAN can hit
the demo — handy for showing it off on a phone next to the laptop.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _bundled_root() -> Path:
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else Path(__file__).resolve().parents[1]


def main() -> None:
    root = _bundled_root()
    # Point Settings at sensible offline defaults when we can't read a
    # .env file (PyInstaller runs the exe from a temp dir).
    os.environ.setdefault("UPSTREAM_TTS_URL", "http://127.0.0.1:8001")
    os.environ.setdefault("UPSTREAM_STT_URL", "http://127.0.0.1:8002")
    os.environ.setdefault("UPSTREAM_TRANSLATE_URL", "http://127.0.0.1:8003")
    os.environ.setdefault("UPSTREAM_ADMIN_URL", "http://127.0.0.1:8004")

    import uvicorn

    host = os.environ.get("GATEWAY_HOST", "127.0.0.1")
    port = int(os.environ.get("GATEWAY_PORT", "8000"))
    print(f"AaaS Gateway starting on http://{host}:{port}")
    print(f"  bundled assets: {root}")
    print(f"  demo URL:       http://{host}:{port}/demo/jajpur-collectorate/")
    uvicorn.run("app.main:app", host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
