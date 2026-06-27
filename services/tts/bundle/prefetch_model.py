"""One-shot: download the Meta MMS-TTS weights into ./models/.

Pulls **three checkpoints** so the bundled exe can speak Odia, Hindi,
and English without hitting the network at demo time. Together the
weights total ~450 MB — still well under the bundle budget (~2 GB),
and small enough that the USB-stick copy stays under a minute.

Run once before building the PyInstaller bundle. Re-running is
idempotent: ``transformers`` reuses the HF cache, so subsequent runs
only download whatever's missing or updated.

Override the list with ``AAAS_TTS_PREFETCH_LANGS=or,hi,en`` (or a
subset) if you want to skip a language — e.g. to ship an Odia-only
bundle for a bandwidth-constrained build machine.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = REPO_ROOT / "models"

# Keep the list in sync with app/config.py::DEFAULT_LANGUAGE_MODELS.
MODEL_IDS: dict[str, str] = {
    "or": "facebook/mms-tts-ory",
    "hi": "facebook/mms-tts-hin",
    "en": "facebook/mms-tts-eng",
}


def _selected_langs() -> list[str]:
    raw = os.environ.get("AAAS_TTS_PREFETCH_LANGS", "").strip()
    if not raw:
        return list(MODEL_IDS)
    picked = [s.strip().lower() for s in raw.split(",") if s.strip()]
    unknown = [s for s in picked if s not in MODEL_IDS]
    if unknown:
        print(
            f"! unknown lang(s) {unknown!r} in AAAS_TTS_PREFETCH_LANGS — "
            f"known: {list(MODEL_IDS)}",
            file=sys.stderr,
        )
        return []
    return picked


def main() -> int:
    langs = _selected_langs()
    if not langs:
        return 2
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    from transformers import AutoTokenizer, VitsModel

    for lang in langs:
        model_id = MODEL_IDS[lang]
        print(f"-> downloading {lang}: {model_id} into {CACHE_DIR}")
        VitsModel.from_pretrained(model_id, cache_dir=str(CACHE_DIR))
        AutoTokenizer.from_pretrained(model_id, cache_dir=str(CACHE_DIR))
    print(f"OK - {len(langs)} model(s) cached, bundle is ready to build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
