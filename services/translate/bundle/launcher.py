"""Entry-point the PyInstaller Translate exe runs.

Pins the engine to ``mock`` at the launcher level because the bundle
ships without torch/transformers — loading NLLB-200 (or IndicTrans2)
would fail on import. Source builds default to ``nllb`` (see
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
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("HF_HOME", str(models_dir))
    os.environ.setdefault("AAAS_TRANSLATE_MODEL_CACHE_DIR", str(models_dir))
    # Bundle ships without torch, so NLLB/IndicTrans2 can't load. Use the
    # Google web endpoint (no key, real Odia for any text) and let it fall
    # back to the curated mock corpus automatically when offline. Override
    # with AAAS_TRANSLATE_ENGINE=mock for a fully-offline-only build.
    os.environ.setdefault("AAAS_TRANSLATE_ENGINE", "google")

    import uvicorn

    host = os.environ.get("TRANSLATE_HOST", "127.0.0.1")
    port = int(
        os.environ.get(
            "TRANSLATE_PORT", os.environ.get("AAAS_TRANSLATE_TRANSLATE_PORT", "8003")
        )
    )
    print(f"AaaS Translate starting on http://{host}:{port}")
    print(f"  model cache: {models_dir}")
    uvicorn.run("app.main:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
