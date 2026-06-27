"""Entry-point the PyInstaller STT exe runs.

Pins the engine to ``mock`` at the launcher level because the bundle
ships without torch/transformers — loading IndicWav2Vec would fail on
import. Source builds default to ``indic_wav2vec`` (see
``app/config.py``); the bundle is the deliberate exception. To ship a
real-engine bundle, rebuild with the ``[indic]`` extra and pre-fetched
weights, then unset the override below.
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
    models_dir = root / "models"
    # Offline defaults so a cold laptop never tries to phone home.
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("HF_HOME", str(models_dir))
    os.environ.setdefault("AAAS_STT_MODEL_CACHE_DIR", str(models_dir))
    # Bundle ships without torch — force mock so the config default
    # (indic_wav2vec) doesn't trigger a noisy load-failure warning on
    # every cold start. Override with AAAS_STT_ENGINE=indic_wav2vec if
    # you built a real-engine bundle.
    os.environ.setdefault("AAAS_STT_ENGINE", "mock")

    import uvicorn

    host = os.environ.get("STT_HOST", "127.0.0.1")
    port = int(os.environ.get("STT_PORT", os.environ.get("AAAS_STT_STT_PORT", "8002")))
    print(f"AaaS STT starting on http://{host}:{port}")
    print(f"  model cache: {models_dir}")
    uvicorn.run("app.main:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
