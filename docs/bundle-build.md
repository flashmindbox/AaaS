# Building the judge-laptop demo bundle

This page is for **the AaaS maintainers**, not for the students who run the
demo. If you are a student running the demo, read
`scripts/bundle_assets/README-for-students.txt` instead.

## What "the bundle" is

`dist/AaaS-Demo/` is a zero-install Windows folder that the Smart Odisha
Hackathon team carries on a USB stick. Double-clicking `start.bat` inside it
boots the full AaaS stack on any Windows 10/11 x64 laptop with no Python,
no pip, and no network. The four bundled services are:

- **Gateway** (port 8000) — HTTP proxy, API-key auth, audit logging, and
  the static host for the widget, demo sites, and admin dashboard.
- **TTS** (port 8001) — neural speech synthesis in Odia, Hindi, and
  English (three Meta MMS-TTS checkpoints — `-ory`, `-hin`, `-eng`).
  Ships with all three model weights prefetched (~450 MB total).
  See `services/tts/README.md` for model details.
- **STT** (port 8002) — speech-to-text. Ships a zero-weight mock engine
  by default; real engines (IndicWav2Vec / faster-whisper) are opt-in.
- **Translate** (port 8003) — Indic↔English translation. Mock-by-corpus
  by default; AI4Bharat IndicTrans2 distilled-200M is the opt-in upgrade.

The whole bundle is a [PyInstaller](https://pyinstaller.org) single-folder
build of those four services, plus the vanilla-JS widget, plus the demo
sites, plus a handful of PowerShell helpers.

Target size: ~1.3 GB on disk, ~950 MB zipped (mocks for STT + Translate
add ~80 MB combined). Torch in the TTS bundle dominates — if the total
ever grows past ~1.6 GB, something is leaking (see *Troubleshooting*
below).

## One-command rebuild

From the repo root, on the dev machine:

```bash
python scripts/build_bundle.py
```

That is the only supported build path. `services/*/build/` and
`services/*/dist/` are intermediate artefacts — don't ship them directly.

### Flags

| Flag | Use |
|---|---|
| `--clean` | Wipe `services/*/{.venv,build,dist}` and rebuild from scratch. Use before a release or after a dep bump. |
| `--skip-tts` | Reuse `services/tts/dist/` — cuts 2-3 minutes when iterating on the other services. |
| `--skip-stt` | Reuse `services/stt/dist/` — cuts ~30 s. |
| `--skip-translate` | Reuse `services/translate/dist/` — cuts ~30 s. |
| `--skip-gw` | Reuse `services/gateway/dist/` — cuts another minute when iterating on backends. |
| `--no-smoke` | Skip per-service HTTP smoke tests. Dangerous; use only if you have already run them manually. |
| `--no-bundle-smoke` | Skip the final end-to-end run of the assembled bundle. Even more dangerous — the script prints `BUNDLE UNVERIFIED` if you use this. |

## What the orchestrator does, step by step

1. **Preflight** — Python 3.12+, 3 GB free disk, all required bundle assets present under `scripts/bundle_assets/`.
2. **TTS build** — fresh venv under `services/tts/.venv/`, install `.[dev,bundle]` (pulls PyInstaller), run `bundle/prefetch_model.py` if `models/` is empty, then `pyinstaller bundle/aaas_tts.spec`. First prefetch pulls ~450 MB from Hugging Face (three MMS checkpoints — `-ory`, `-hin`, `-eng`); subsequent builds are fully offline.
3. **TTS smoke** — launch `services/tts/dist/aaas-tts/aaas-tts.exe` on port 8011, poll `/readyz` until 200, POST `{"text":"ନମସ୍କାର"}`, assert ≥10 KB of `audio/wav`, kill.
4. **STT build** — same pattern against `services/stt/bundle/aaas_stt.spec`. Default mock engine has no torch/transformers dependency, so bundle is ~50 MB.
5. **STT smoke** — launch on port 8013, poll `/readyz`, POST a tiny multipart audio blob, assert JSON transcript with `engine=mock`.
6. **Translate build** — same pattern against `services/translate/bundle/aaas_translate.spec`.
7. **Translate smoke** — launch on port 8014, poll `/readyz`, POST `{"text":"ନମସ୍କାର","src_lang":"or","tgt_lang":"en"}`, assert JSON with `tgt_lang=en`.
8. **Gateway build** — same pattern, `services/gateway/.venv/` → `pyinstaller bundle/aaas_gateway.spec`.
9. **Gateway smoke** — launches gateway + TTS, polls `/healthz`, fetches `/widget.js` and `/demo/jajpur-collectorate/`, does a full synthesise round-trip with the seeded dev tenant `aaas_live_0000…0000`.
10. **Assemble** `dist/AaaS-Demo/` — copies the four `dist/aaas-*` trees plus `scripts/bundle_assets/{start.bat, tools/, README-for-students.txt, LICENSE-THIRD-PARTY.txt}`. A tripwire walks the assembled tree and aborts if it finds a `.venv/`, `__pycache__`, `.env`, or `out-through-gateway.wav`.
11. **Bundle smoke** — runs through the real `portcheck.ps1` to pick four ports, starts all four exes in dependency order (TTS → STT → Translate → Gateway), hits the demo page, synthesises Odia, round-trips `/translate/translate`, *and* negatively tests TTS with English text against the default Odia model to confirm the MMS tokeniser rejects off-script input with a clean 4xx (so the widget shows a TTS error instead of playing 0-byte "audio"). Meta MMS-TTS is the only TTS engine — there is no widget Web-Speech fallback.
12. **Report** — prints bundle size, SHA-256 of all four exes, next steps. Hashes also go into `dist/AaaS-Demo.sha256` for the release record.

Any step failure aborts the whole build; the orchestrator exits non-zero
with a loud `ERROR:` line. It never silently ships a broken bundle.

## Files you touch when changing the bundle

| Thing to change | File |
|---|---|
| Launcher behaviour (ports, startup order, browser) | `scripts/bundle_assets/start.bat` |
| Port-conflict scan range | `scripts/bundle_assets/tools/portcheck.ps1` |
| Readiness timeout | `scripts/bundle_assets/tools/wait-ready.ps1` |
| Prewarm text or API key | `scripts/bundle_assets/tools/prewarm.ps1` |
| Browser preference order | `scripts/bundle_assets/tools/open-browser.ps1` |
| Student-facing troubleshooting | `scripts/bundle_assets/README-for-students.txt` |
| Third-party notices | `scripts/bundle_assets/LICENSE-THIRD-PARTY.txt` |
| What gets bundled inside each exe | `services/{tts,stt,translate,gateway}/bundle/aaas_*.spec` |
| What env vars the exes set at boot | `services/*/bundle/launcher.py` |
| Model cache (Odia VITS weights) | `services/tts/models/` — regenerated by `services/tts/bundle/prefetch_model.py` |

**Do not** hand-edit `dist/AaaS-Demo/` — the orchestrator wipes it on every
run. Changes land in `scripts/bundle_assets/` or the service specs.

## Licence footnote (important for any commercial follow-up)

The Odia voice ships as **Meta MMS-TTS-ory**, which is licensed under
[CC-BY-NC 4.0](https://huggingface.co/facebook/mms-tts-ory). That is fine
for a hackathon demo but **forbids commercial use**. Before shipping a
pilot, swap to one of:

- [AI4Bharat Indic-TTS](https://github.com/AI4Bharat/Indic-TTS) Odia voice (licence: check per-voice)
- An in-house voice cloned from a speaker with a signed release
- A commercial vendor with an API key

The swap is localised: `services/tts/app/engine/mms.py`,
`services/tts/bundle/prefetch_model.py`, and `services/tts/bundle/aaas_tts.spec`.
Everything else (gateway, widget, demo sites) is model-agnostic.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `pyinstaller` succeeds but exe crashes at launch with `ModuleNotFoundError` | Hidden import missed by the spec | Add the module to `hiddenimports` (see existing `collect_submodules("transformers.models.vits")`) |
| Bundle is >1.5 GB | `matplotlib`/`pandas`/`tkinter` slipped in via a transitive dep | Extend the `excludes=` list in the spec file |
| TTS `/readyz` never returns 200 in smoke test | Model files not in `services/tts/models/` | Re-run `python services/tts/bundle/prefetch_model.py` |
| Gateway `/demo/jajpur-collectorate/` returns 404 | `apps/widget/dist` or `apps/demo-sites` were not present at build time | Rebuild the widget (`python scripts/build_widget.py` — inlines the Noto Sans Oriya woff2 base64, a plain `cp` from `src/` would ship the `__AAAS_NOTO_ORIYA_B64__` placeholder and break Odia rendering) then rerun the bundle build |
| Odia conjuncts render as "base + mark" on the demo page | Widget was shipped from `src/` instead of `dist/`, or the font placeholder wasn't substituted | Check `apps/widget/dist/widget.js` for the literal string `__AAAS_NOTO_ORIYA_B64__` — if present, run `python scripts/build_widget.py`. The gateway test `tests/test_static_mounts.py::test_widget_js_has_inlined_font_not_placeholder` catches this automatically when `services/gateway/` tests run. |
| WCAG scanner doesn't return violations offline | `apps/admin/vendor/axe.min.js` missing | Re-copy axe from `node_modules/.pnpm/axe-core@*/node_modules/axe-core/axe.min.js` to `apps/admin/vendor/axe.min.js`. The admin page loads it from the same origin so there's no CDN dependency. |
| `start.bat` on the target laptop exits with `ERROR: services did not start in time.` | Defender quarantined `aaas-tts.exe` **or** torch DLLs blocked by antivirus | README tells students to add a Defender exclusion for the folder |
| First click on "Read this page" is slow (>3 s) on a warm machine | Prewarm skipped or failed | Check `logs/launcher.log` for the prewarm line; verify the seed API key in `prewarm.ps1` still matches `_seed_dev_repository` in the gateway |

## After a successful build

Sanity check before you declare victory:

```powershell
# From the repo root, on the dev machine:
dist\AaaS-Demo\start.bat
```

If that opens the demo and reads the Jajpur page in Odia, the bundle is
good. Copy the folder onto a USB stick (do not zip — extraction on a slow
laptop eats demo time) and run the rehearsal checklist at
`docs/demo-rehearsal-checklist.md` on a **different** Windows laptop before
hackathon day.
