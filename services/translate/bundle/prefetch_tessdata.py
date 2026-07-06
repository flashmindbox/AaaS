"""Download Tesseract traineddata for the OCR endpoint.

Fetches the *fast* variants of English, Odia and Hindi into
``services/translate/models/tessdata/`` — the project-local directory
the OCR engine passes to Tesseract via ``--tessdata-dir``, so nothing
is written into Program Files and the same files ship in the bundle.

Run once (idempotent):

    cd services/translate
    python bundle/prefetch_tessdata.py
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

LANGS = ["eng", "ori", "hin"]
BASE = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/{lang}.traineddata"
DEST = Path(__file__).resolve().parent.parent / "models" / "tessdata"


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    for lang in LANGS:
        target = DEST / f"{lang}.traineddata"
        if target.is_file() and target.stat().st_size > 100_000:
            print(f"[tessdata] {lang}: already present ({target.stat().st_size:,} bytes)")
            continue
        url = BASE.format(lang=lang)
        print(f"[tessdata] downloading {lang} from {url} ...")
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                data = resp.read()
        except OSError as exc:
            print(f"[tessdata] FAILED for {lang}: {exc}", file=sys.stderr)
            return 1
        target.write_bytes(data)
        print(f"[tessdata] {lang}: wrote {len(data):,} bytes -> {target}")
    print(f"[tessdata] done — set nothing; the engine finds {DEST} automatically")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
