# AaaS Translation service

Multilingual translation for the AaaS gateway. Same shape as the STT
and TTS services: pluggable engine Protocol, Meta NLLB-200 distilled-600M
as the default, mock corpus as an explicit opt-out for offline / bundle / CI.

## Quick start

```bash
cd services/translate
python -m venv .venv && .venv/Scripts/activate
pip install -e ".[dev,indic]"
python bundle/prefetch_model.py       # ~2.4 GB, one-shot
uvicorn app.main:app --port 8003 --reload
```

The first `/readyz` call after startup returns 503 while the model is
loading (~20 s on CPU from cold cache, ~5 s from warm disk); the
widget handles that transparently.

## API

- `GET /healthz` / `GET /readyz` / `GET /version`
- `POST /translate`
  ```json
  {"text": "ମୋ ନାମ ପ୍ରିୟା", "src_lang": "or", "tgt_lang": "en"}
  ```
  Returns:
  ```json
  {"text": "My name is Priya", "src_lang": "or", "tgt_lang": "en", "engine": "nllb"}
  ```
- `POST /simplify` — plain-language rewriting ("Easy Read" in the widget)
  ```json
  {"text": "Applicants shall furnish the requisite documents w.e.f. 01.01.2026.", "lang": "en"}
  ```
  Returns:
  ```json
  {"text": "Applicants shall give the required documents with effect from 01.01.2026.", "lang": "en", "engine": "rules"}
  ```
- `POST /ocr` — scanned notices (multipart: `file` = PNG/JPEG/WebP/PDF, `lang` = or/hi/en/auto)
  ```
  curl -F "file=@notice-scan.png" -F "lang=en" .../ocr
  ```
  Returns:
  ```json
  {"text": "GOVERNMENT OF ODISHA ...", "lang": "en", "engine": "tesseract",
   "pages": [{"page": 1, "text": "...", "source": "ocr"}]}
  ```
  `source` per page: `"text-layer"` (born-digital PDF page — extracted
  directly, no OCR), `"ocr"` (genuine scan), `"mock"` (fallback engine).

## Simplification (Easy Read)

`POST /simplify` rewrites bureaucratic prose into shorter, plainer
sentences using a **rule-based engine** (`app/engine/simplify_rules.py`)
— no ML, no network, no extra install, so it ships in the PyInstaller
bundle and works fully offline. The pipeline: strip legal boilerplate →
expand abbreviations (w.e.f., govt., s/o …) → glossary substitution of
legalese for everyday words (~45 English + ~10 Odia entries, extensible
one dict line at a time) → split overlong sentences at semicolons and
conjunctions. Output is idempotent (simplifying twice changes nothing).

The engine sits behind the same Protocol pattern as translation
(`app/engine/simplify_base.py`), so an LLM-backed simplifier can be
slotted in later without touching the route or the widget. Reached
through the gateway at `/translate/simplify` (catch-all proxy — no
gateway changes needed).

The widget's "Easy Read this page" button calls this per text node;
when the user's language differs from the page's, it chains
simplify → `/translate`, so an English notice renders as plain Odia.

## OCR (scanned notices)

`POST /ocr` unlocks the documents government portals actually publish:
scans of stamped paper (images and image-only PDFs) that read-aloud,
translate and screen readers are blind to. Engine: **Tesseract** via
pytesseract — classic CPU OCR, sub-second per page, no torch — behind
the same Protocol pattern (`app/engine/ocr_base.py`) so Surya or the
planned `content-adapter` service can slot in later. PDFs (pypdfium2)
use the embedded text layer when present and only rasterize + OCR
genuinely scanned pages.

Setup (one-time):

```powershell
winget install UB-Mannheim.TesseractOCR   # the binary (eng included)
cd services/translate
python bundle/prefetch_tessdata.py        # eng/ori/hin -> models/tessdata
pip install -e ".[dev,ocr]"               # pytesseract, pypdfium2, Pillow
```

The engine resolves the binary from `AAAS_TRANSLATE_TESSERACT_CMD`,
PATH, or the standard Windows install dir, and points
`TESSDATA_PREFIX` at `models/tessdata`. If the binary or the `[ocr]`
extras are missing, the service logs `translate.ocr_engine_load_failed`
and swaps in a deterministic **mock** (canned notice text) — OCR being
unavailable never affects `/readyz` or the translate/simplify routes.

The widget's "Read a document to me" button drives this: the widget
finds the page's scans/PDFs (chooser when there are several) → `/ocr`
→ simplify → translate → large-print modal that starts reading aloud
automatically. Limits: 15 MB per upload, first 10 PDF pages.

## Backends

| Engine | Install | Notes |
|---|---|---|
| `nllb` | **default**, `pip install -e .[indic]` + `python bundle/prefetch_model.py` | Meta NLLB-200 distilled-600M, 200 languages, CC-BY-NC-4.0, CPU-capable (~1-2 s per short sentence). Not gated on HuggingFace — clones and runs from a fresh environment. |
| `indictrans2` | `pip install -e .[indic]` + `huggingface-cli login` + accept access terms on the HF model page + `AAAS_TRANSLATE_PREFETCH_ENGINE=indictrans2 python bundle/prefetch_model.py` | AI4Bharat IndicTrans2 distilled-200M. Marginally better Indic quality than NLLB, MIT-licensed (commercial OK), but the HF repos are gated. |
| `mock` | always available | Curated parallel corpus of ~15 demo phrases. Off-corpus requests come back as `[src->tgt] original text`. Used by the PyInstaller bundle (no torch) and by CI where deterministic output matters; force explicitly with `AAAS_TRANSLATE_ENGINE=mock`. |

If a real engine fails to load (missing extras, missing weights, OOM),
the service now stays **unready** — `/readyz` returns 503 and the
widget surfaces a `Translation unavailable` error. Previously it
silently fell back to the mock corpus, which hid broken state from
the UI.

## Bundle

Rides along with the other three services in the judge-laptop USB
bundle. One-shot rebuild: `python scripts/build_bundle.py` from the
repo root. Iterate on just this service with
`python scripts/build_bundle.py --skip-tts --skip-stt --skip-gw`.

The bundle ships the **mock** engine only (no torch). Real NLLB is
reachable via Docker Compose or by rebuilding with the `[indic]`
extras and pre-fetched weights; see `docs/bundle-build.md`.

See [`docs/plan-v2.md`](../../docs/plan-v2.md) for context.
