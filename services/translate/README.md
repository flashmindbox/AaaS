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
