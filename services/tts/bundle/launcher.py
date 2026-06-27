"""Entry-point the PyInstaller exe runs.

Sets the model cache to the bundled ``models/`` folder (so the shipped
weights are used instead of re-downloading into the user's HF cache),
then hands off to uvicorn.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _bundled_root() -> Path:
    # PyInstaller sets ``sys._MEIPASS`` to the unpacked temp dir when
    # running from a frozen exe. In dev it won't exist, so we fall back
    # to this file's parent.
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else Path(__file__).resolve().parents[1]


def main() -> None:
    root = _bundled_root()
    models_dir = root / "models"
    # Tell transformers + our Settings to read from the bundled folder.
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("HF_HOME", str(models_dir))
    os.environ.setdefault("MODEL_CACHE_DIR", str(models_dir))

    import uvicorn

    host = os.environ.get("TTS_HOST", "127.0.0.1")
    port = int(os.environ.get("TTS_PORT", "8001"))
    print(f"AaaS TTS starting on http://{host}:{port}")
    print(f"  model cache: {models_dir}")
    uvicorn.run("app.main:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
