"""One-shot: download the translate service's model weights into ./models/.

Defaults to Meta NLLB-200 distilled-600M (~2.4 GB), which is the default
engine because it isn't gated on Hugging Face — anyone can clone and run.

Override with ``AAAS_TRANSLATE_PREFETCH_ENGINE=indictrans2`` to pull the
AI4Bharat IndicTrans2 distilled-200M pair instead. IndicTrans2 is
slightly better on Indic pairs but its HF repos are gated, so you also
have to run ``huggingface-cli login`` and accept the access terms on
the model page first.

Re-running is idempotent: ``transformers`` reuses the HF cache, so
subsequent runs only download whatever's missing or updated.

License reminder:

- NLLB-200 is CC-BY-NC-4.0 — non-commercial, same as Meta MMS-TTS.
- IndicTrans2 is MIT — commercial OK, but requires HF auth to download.

``docs/bundle-build.md`` already notes the need to swap the TTS model
before any commercial pilot; the same applies to NLLB.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = REPO_ROOT / "models"

# Map engine -> list of model IDs to pre-download. Keep in sync with
# app/engine/nllb.py::_MODEL_ID and
# app/engine/indictrans2.py::_INDIC_TO_EN / _EN_TO_INDIC.
MODELS_BY_ENGINE: dict[str, list[str]] = {
    "nllb": ["facebook/nllb-200-distilled-600M"],
    "indictrans2": [
        "ai4bharat/indictrans2-indic-en-dist-200M",
        "ai4bharat/indictrans2-en-indic-dist-200M",
    ],
}


def _selected_engine() -> str:
    raw = os.environ.get("AAAS_TRANSLATE_PREFETCH_ENGINE", "").strip().lower()
    if not raw:
        return "nllb"
    if raw not in MODELS_BY_ENGINE:
        print(
            f"! unknown engine {raw!r} — known: {sorted(MODELS_BY_ENGINE)}",
            file=sys.stderr,
        )
        return ""
    return raw


def main() -> int:
    engine = _selected_engine()
    if not engine:
        return 2
    model_ids = MODELS_BY_ENGINE[engine]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError:
        print(
            "! transformers not installed — run "
            "`pip install -e .[indic]` in services/translate first",
            file=sys.stderr,
        )
        return 2

    trust_remote = engine == "indictrans2"
    for model_id in model_ids:
        print(f"-> downloading {engine}: {model_id} into {CACHE_DIR}")
        AutoTokenizer.from_pretrained(
            model_id, trust_remote_code=trust_remote, cache_dir=str(CACHE_DIR)
        )
        AutoModelForSeq2SeqLM.from_pretrained(
            model_id, trust_remote_code=trust_remote, cache_dir=str(CACHE_DIR)
        )
    print(
        f"OK - {len(model_ids)} model(s) cached for engine={engine}, "
        f"translate service is ready to start"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
