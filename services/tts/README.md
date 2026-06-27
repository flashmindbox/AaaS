# AaaS TTS — Offline Odia / Hindi / English neural voice

FastAPI service that turns text into natural-sounding speech, running
entirely on the local laptop. No GPU, no cloud, no internet once the
models have been cached.

## Backend: Meta MMS-TTS

The service uses three **Meta MMS-TTS** VITS checkpoints side by side,
routed by the request's `lang` field. All three share one code path,
one tokeniser shape, and one serving container — they just point at
different weights on disk:

| lang | Model                 | HF id                    | Notes                     |
|------|-----------------------|--------------------------|---------------------------|
| `or` | MMS-TTS-ory (default) | `facebook/mms-tts-ory`   | Eager-loaded at startup   |
| `hi` | MMS-TTS-hin           | `facebook/mms-tts-hin`   | Lazy-loaded on first call |
| `en` | MMS-TTS-eng           | `facebook/mms-tts-eng`   | Lazy-loaded on first call |

Properties common to all three:

| Property      | Value                                     |
|---------------|-------------------------------------------|
| Model size    | ~150 MB each (~450 MB total)              |
| Sample rate   | 16 000 Hz                                 |
| CPU latency   | ~0.3–1.5 s for a short sentence           |
| License       | CC-BY-NC 4.0 (research / hackathon OK)    |

Why MMS:

- **Odia coverage is first-class.** Meta trained MMS on 1,100+
  languages including Odia (`ory`); conjuncts, matras and rare
  consonants come out far better than any generic multilingual TTS.
- **Real-time on CPU.** ~150 MB per language, sub-second for a short
  sentence on a modern laptop. No GPU required.
- **Hugging Face convenience.** `transformers.VitsModel` loads it in
  one line and the weights can be shipped alongside the PyInstaller
  exe for a fully offline install.

The engine:

- NFC-normalises input and strips zero-width joiners before tokenising
  so browser-pasted text doesn't land as `<unk>` in the tokeniser.
- Chunks long inputs on sentence terminators (`.!?।॥`) and splices
  per-chunk waveforms with a 120 ms silence — VITS attention degrades
  past ~500 chars and chunking keeps prosody stable.
- Removes the vocoder's residual DC offset and peak-normalises to
  -1 dBFS so playback doesn't click or clip.

## Endpoints

| Method | Path          | Description                                                   |
|--------|---------------|---------------------------------------------------------------|
| GET    | `/healthz`    | Liveness — always `200` while the proc is up                  |
| GET    | `/readyz`     | `200` once the default-language model is loaded; else `503`   |
| GET    | `/version`    | Build metadata                                                |
| GET    | `/voices`     | Default language + per-language model ids                     |
| POST   | `/synthesise` | Body `{"text":"...", "lang":"or"\|"hi"\|"en"}` → `audio/wav`  |

`lang` is optional. If omitted, the service uses the configured
`default_language` (Odia). The response carries an `X-Lang` header
echoing the language that was actually used.

Upstream is called only by the gateway, which strips `X-API-Key` and
injects `X-Tenant-*` before forwarding.

## Local dev

```bash
cd services/tts
pip install -e .[dev]
cp .env.example .env
uvicorn app.main:app --reload --port 8001
```

First boot downloads the three MMS checkpoints into `./models/`
(~450 MB total). Subsequent boots are fully offline. To skip a language
(e.g. an Odia-only dev build) set
`AAAS_TTS_PREFETCH_LANGS=or` before running `bundle/prefetch_model.py`.

### Test the real endpoint

```bash
# Odia (default when lang is omitted)
curl -X POST http://localhost:8001/synthesise \
     -H "Content-Type: application/json" \
     --data '{"text":"ନମସ୍କାର, ମୁଁ ଓଡ଼ିଶା ସରକାରଙ୍କ ଏକ ଉଦ୍ୟୋଗ"}' \
     --output hello-or.wav

# Hindi
curl -X POST http://localhost:8001/synthesise \
     -H "Content-Type: application/json" \
     --data '{"text":"नमस्ते, मैं ओडिशा सरकार का एक कार्यक्रम हूँ।","lang":"hi"}' \
     --output hello-hi.wav

# English
curl -X POST http://localhost:8001/synthesise \
     -H "Content-Type: application/json" \
     --data '{"text":"Hello, I am an Odisha Government programme.","lang":"en"}' \
     --output hello-en.wav
```

### Run the test suite

```bash
python -m pytest tests/
```

Tests use a `FakeEngine` fixture, so they don't download weights and
run in under a second.

## Portable bundle

The TTS service is shipped as part of the full judge-laptop bundle
produced by the repo-root orchestrator:

```bash
python scripts/build_bundle.py
```

That single command creates `services/tts/.venv`, runs
`bundle/prefetch_model.py`, invokes `pyinstaller bundle/aaas_tts.spec`,
smoke-tests `services/tts/dist/aaas-tts/aaas-tts.exe` against `/readyz`
and a real Odia synthesis, and assembles the final folder at
`dist/AaaS-Demo/`. See `docs/bundle-build.md` for the flag reference and
troubleshooting guide.

To build only this service in isolation (useful when iterating):

```bash
python scripts/build_bundle.py --skip-stt --skip-translate --skip-gw
```

The resulting `services/tts/dist/aaas-tts/` folder is self-contained:
Python runtime, torch, transformers, and the pre-downloaded MMS-TTS
weights. Double-clicking `aaas-tts.exe` inside that folder brings the
service up on `127.0.0.1:8001` with zero Python install on the target
machine.

## Roadmap

- ONNX int8 export for 2–3× CPU speedup (Phase 1.2)
- Simple in-memory LRU cache keyed on input text hash (hot phrases)
