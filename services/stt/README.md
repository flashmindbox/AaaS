# AaaS STT service

Speech-to-text for the AaaS gateway. Pluggable engine Protocol: mock,
IndicWav2Vec (Odia), and faster-whisper (English / multi) all implement
the same shape so the FastAPI layer is identical.

## Quick start

```bash
cd services/stt
python -m venv .venv && .venv/Scripts/activate   # PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --port 8002 --reload
```

Default engine is `indic_wav2vec` (AI4Bharat IndicWav2Vec-Odia). Install
the matching extra first:

```bash
pip install -e ".[indic]"      # Odia (AI4Bharat IndicWav2Vec) — the default
# or
pip install -e ".[whisper]"    # English + Hindi (faster-whisper-small)
```

If the extras aren't installed the lifespan catches the `ImportError`
and falls back to `mock` automatically — canned Odia / Hindi / English
phrases keyed on the audio bytes hash so rehearsals stay deterministic.
To force mock explicitly (bundle, CI, offline smoke tests) set
`AAAS_STT_ENGINE=mock` in your `.env`.

## API

- `GET /healthz` → `{"status": "ok", "service": "stt", "engine": "mock"}`
- `GET /readyz` → 200 once engine is loaded, 503 while loading
- `POST /transcribe` multipart form → `{"text", "language", "confidence", "engine"}`
  - `audio` field: WAV/OGG/webm blob
  - `language` field (optional): `or` / `hi` / `en` language hint

## Ports

Default port is 8002. Gateway proxies `/stt/*` at the configured
`AAAS_GATEWAY_UPSTREAM_STT_URL` (which is `http://localhost:8002` in
the default `.env`).

## Bundle

For the judge-laptop USB bundle, this service rides along with the TTS,
Translate, and gateway bundles. One-shot rebuild:
`python scripts/build_bundle.py` from the repo root. Iterate on just
this service with `python scripts/build_bundle.py --skip-tts --skip-translate --skip-gw`.

The bundle ships the **mock** engine only (fast, zero-weight). Real
Indic / Whisper backends are reachable via Docker Compose by rebuilding
with `STT_ENGINE_EXTRA=indic` (or `=whisper`) in the repo-root `.env`.

See [`docs/plan-v2.md`](../../docs/plan-v2.md) for the full-product
context and phasing.
