# AaaS Full-Product Plan — v2

Status: **active** (supersedes v1 judge-laptop-bundle-only plan).

## Why this plan exists

The v1 plan delivered a vertical-slice demo (TTS + Gateway only, plus a widget) and a PyInstaller bundle. That bundle proved fragile — two separate Windows-encoding bugs broke it during rehearsal — and it only covers 2 of the 6 components pitched in `Aas.pdf`. The hackathon jury will evaluate against the deck, not against whatever a single slice demonstrates, so the v1 scope is insufficient.

This v2 plan delivers the pitched components as a full working product, with both a cloud-hosted demo (primary) and the local bundle (offline backup). (The accessible-examination module has since been descoped to the roadmap — see the table below.)

## Pitched components vs. planned delivery

| # | Component (`Aas.pdf`) | State before v2 | v2 target |
|---|---|---|---|
| 1 | Speech-to-Text | Gateway proxy stub only, no upstream | New `services/stt/` — mock backend first, AI4Bharat IndicWav2Vec / faster-whisper second |
| 2 | Text-to-Speech + Screen Reader | Delivered in v1 | Keep; fix any remaining bundle bugs |
| 3 | Accessibility API Gateway | Delivered in v1 | Extend with `/translate/*`, in-gateway `/admin/api/*`, audit middleware |
| 4 | Language Translation | Not built | New `services/translate/` — mock bilingual dict first, IndicTrans2 distilled second |
| 5 | Accessible Examination | Not built | Descoped — roadmap item (`PLAN.md` Phase 3); the BSE Odisha exam-board demo tenant remains |
| 6 | Admin Dashboard | Not built (proxy route only) | New `apps/admin/` — tenants, keys, usage, axe-core WCAG 2.1 AA scanner |

## Strategic pivot: cloud demo + bundle as backup

**Primary demo path:** judges open a URL. A single Docker Compose stack (gateway + 3 python services + caddy for TLS) runs on a small VPS or fly.io. No install, no SmartScreen, no Defender, no port conflicts, no PowerShell encoding bugs, no USB copy.

**Fallback:** the v1 local bundle remains on a USB for offline / no-WiFi scenarios. Both paths run the same code.

## Architecture

```
Browser (judge laptop, any OS)
  demo.aaas/{jajpur,utkal,bse}  -> widget in the corner
  demo.aaas/admin               -> admin dashboard
         |
         | HTTPS
         v
Gateway (services/gateway — extended)
  /tts/*        -> TTS service (existing)
  /stt/*        -> STT service (new proxy)
  /translate/*  -> Translation (new proxy)
  /admin/api/*  -> in-gateway admin impl (new)
  /widget.js    -> widget bundle
  /demo/*       -> demo site HTML
  /admin/*      -> admin dashboard HTML
  Audit middleware: every request -> ring-buffer consumed by admin
  Auth: X-API-Key, in-memory seed tenant
         |
   +-----+------+--------+
   v            v        v
 TTS          STT    Translate
 MMS-TTS-ory  IndicWav2Vec  IndicTrans2
```

## Mock-first implementation strategy

The v2 build ships each new service with a pluggable engine Protocol and a **mock backend by default**. This means:
- The demo UI story comes together end-to-end within a day.
- Every feature is testable and shippable before we commit to a heavyweight model download.
- Swapping to a real model is one environment variable flip (`AAAS_STT_ENGINE=indic_wav2vec`).
- If a real model doesn't load (driver, weights, license), the service keeps running with mocks and the demo never goes dark.

## Phasing (always-shippable)

Each phase ends with a strictly-better working demo than the previous.

| Phase | Deliverable | Shippable state |
|---|---|---|
| 0 | TTS bug verification: rerun start.bat post em-dash fix, confirm audio plays | v1 slice works reliably |
| 1 | Scaffold STT + Translate services (mock engines). Wire gateway proxies. | STT/translate endpoints return sensible mock data; widget integrations work |
| 2 | Widget extensions: language picker + mic button. Demo-site sprawl: utkal-university, bse-odisha. | Pitch items #1 and #4 are visibly interactive |
| 3 | Admin dashboard. Audit middleware. WCAG scanner (axe-core). | Pitch item #6 lands |
| 4 | Real model swap-in where feasible: IndicTrans2 distilled for translate, faster-whisper for STT English, IndicWav2Vec for STT Odia. | Production-grade outputs where a model is available |
| 5 | Cloud deploy (docker-compose + caddy). Bundle refresh including STT + Translate. Clean-room rehearsal. | Two independent demo paths proven. |

## Demo script (2-minute judge walkthrough)

> "Priya is a blind student in Jajpur applying to Utkal University."

1. Open `demo/utkal-university/`. Widget auto-announces "Accessibility tools available." Priya presses ଅ → "Read this page" → page reads in Odia.
2. Switch language picker to English → page retranslates → TTS re-reads in English (for her English-speaking helper).
3. Priya taps the mic, speaks her name in Odia, STT fills the name field.
4. Flip to `/admin/`. Tenant list, API key for Utkal, usage chart (Priya's session visible), one-click **Scan WCAG** on the demo site → AA compliance report.
5. "This is one API — the institution drops our widget and gets TTS, STT, translation, and WCAG monitoring. One integration surface, six compliance wins."

Every step degrades predictably: TTS fails → error pill, no speech (MMS is the only engine — no browser-voice fallback); STT fails → keyboard; translate fails → original-language readout; admin fails → slides.

## Model choices

| Concern | Pick | Why |
|---|---|---|
| TTS | MMS-TTS-ory (CC-BY-NC-4.0) | Already bundled, already working. For commercial pilot, swap to AI4Bharat IndicTTS (MIT). Noted in `docs/bundle-build.md`. |
| STT — Odia | AI4Bharat IndicWav2Vec-Odia | Best published Odia WER (~25–30%). |
| STT — English fallback | faster-whisper-small (CTranslate2) | CPU-friendly, 2–5% WER English. |
| Translation | AI4Bharat IndicTrans2 distilled-200M | 22 Indic languages, MIT-licensed, CPU-capable. |
| WCAG scanner | axe-core (MPL-2.0) | Industry-standard accessibility scanner, runs client-side, no backend dep. |
| Dyslexia font | OpenDyslexic (SIL OFL) | The recognised accessibility font. |

## Out of scope (explicit)

- Postgres / Redis / Keycloak. Gateway keeps the in-memory seed tenant.
- Billing / rate-limit enforcement. Audit middleware only **records**.
- Native iOS / Android apps. Web only.
- Streaming STT / WebRTC. Request/response (record → submit → transcript).
- Model fine-tuning. Use published checkpoints.
- Code-signing the bundle. Post-hackathon.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Real STT Odia WER too poor, demo looks broken | Mock engine always on standby; in presentation, pre-record a known-good Odia clip and play it through the system's virtual audio. |
| IndicTrans2 download flaky | Mock engine covers the 5 demo phrases with a curated translation table; swap to real model only once the swap passes smoke tests. |
| Cloud latency to Bhubaneswar venue | Region-pick Mumbai / Singapore; bundle USB is always available. |
| Venue WiFi dead | USB is the fallback; switch paths live. |
| axe-core flags demo sites | Run axe during dev; fix every AA issue before rehearsal. |
| Bundle grows past 4 GB FAT32 limit | Keep folder-of-files layout; no single file >500 MB; budget 3 GB total. |

## Acceptance criteria (definition of done per phase)

A phase is **done** only when:
1. Cloud demo works end-to-end for the phase's new user action.
2. Bundle smoke test still passes (`python scripts/build_bundle.py` green).
3. Killing `aaas-tts.exe` surfaces a clean "TTS unavailable" error in the widget (no browser-voice fallback exists — MMS-TTS is the only engine).
4. Demo script rehearsal recorded end-to-end at least once.

---

*Written 2026-04-21 as the scope redesign after v1 bundle rehearsal exposed scope and fragility gaps.*
