# Demo rehearsal checklist

Run through this on a **clean Windows 10/11 laptop that has never had Python
installed** at least 24 hours before judging. Not the dev machine, not the
laptop where the bundle was built. Every "true negative" here is a disaster
prevented on stage.

## Prerequisites

- [ ] Fresh `dist/AaaS-Demo/` built on the dev machine via `python scripts/build_bundle.py`.
      **Any bundle from before 2026-04-21 22:00 is stale** — pre-Phase-A/B, it's
      missing the widget's inlined Noto Sans Oriya, the Hindi + English TTS voices,
      the dyslexia toggle, the `lang="or"` markup on demo-site Odia spans, and the
      offline axe-core at `apps/admin/vendor/`. Discard the old `dist/AaaS-Demo/`
      and rebuild from scratch (`--clean` if you're reusing a working dir).
- [ ] Bundle folder copied to a USB stick (FAT32 is fine — no single file inside exceeds 500 MB).
- [ ] Backup USB stick from a *different* vendor, with the same bundle on it.
- [ ] The `PITCH/AaaS.pdf` deck on both USB sticks as a slide-only fallback.
- [ ] Decide **before the build** whether the bundle ships mock or real STT / Translate engines.
      Source config now defaults to real (`indic_wav2vec`, `indictrans2`); the bundle launchers
      force `mock` because torch isn't shipped. A real-engine bundle needs the `[indic]` extras
      and pre-fetched weights and grows the USB by ~3 GB.

## Clean-room rehearsal

On the target laptop, with no AaaS services already running:

- [ ] Plug in the USB stick. Copy `AaaS-Demo/` to the Desktop (~60 s typical).
- [ ] Note the copy time. If it is >5 minutes, use the other USB stick on demo day.
- [ ] Double-click `start.bat`.
- [ ] **SmartScreen:** "Windows protected your PC" appears → click "More info" → "Run anyway". Only happens once per machine.
- [ ] Within 60-120 seconds a browser opens to `http://127.0.0.1:8000/demo/jajpur-collectorate/` (or a higher port if 8000 was busy). Four services start in parallel (TTS, STT, Translate, Gateway) so the cold-start is dominated by the TTS model load.
- [ ] The launcher window prints `gateway ready`, `tts ready`, `stt ready`, `translate ready`, and three prewarm lines: `prewarm ok or (<bytes>)`, `prewarm ok hi (<bytes>)`, `prewarm ok en (<bytes>)`. A missing language line means that MMS model failed to warm — the first click in that language will either lag (JIT on first call) or surface a TTS error if the model is truly broken. There is no browser-voice fallback.
- [ ] Click the round ଅ button bottom-right → panel opens → status pill reads `Ready.` (green).
- [ ] **Odia renders correctly:** the `ଅ` FAB glyph is a single clean letter (not a square, not two stacked pieces). The demo page body text renders Odia conjuncts (ରା, ଷ୍ଟ, ଜ୍ଞ) without visible "base + mark" splits — the widget inlines Noto Sans Oriya so this works even on a fresh Windows laptop that has only Kalinga.
- [ ] Click **Read this page** → Odia audio plays within 3 seconds. Status pill reads `Playing…` then `Done.`.
- [ ] Click the mic button → record a short Odia phrase → transcript appears in the panel (mock engine returns a canned phrase; real engine transcribes if `[indic]` was built in).
- [ ] Switch the language picker to **Hindi** → click **Read this page** → audio re-reads in Hindi within ~1-2 s. (Prewarm covers or/hi/en, so there's no first-click JIT stall.) If Hindi stalls for 10+ s, check the launcher window for a missing `prewarm ok hi` line.
- [ ] Switch the language picker to **English** → click **Read this page** → audio re-reads in English within ~1-2 s. Same prewarm guarantee.
- [ ] Click **Stop** mid-sentence → audio stops within 0.5 seconds.
- [ ] Tick **Dyslexia mode** in the widget panel → the demo page visibly reflows: larger body text, warm off-white background (`#fbf7ef`), Comic Sans / system sans fallback on Latin, Noto Sans Oriya kept for Odia paragraphs, line-height clearly looser. Un-tick → page returns to its original styling. Reload the tab → the setting persists (the panel's checkbox comes back ticked and styles re-apply).
- [ ] Navigate to `/exam/` in the address bar → exam module loads with OpenDyslexic font, questions narrate on focus, keyboard nav works.
- [ ] On the BSE demo page, scroll to **Result look-up**, fill the form with anything, click **Check result** → an inline "Demo form." note appears below the form with `role="status"` (no browser `alert()` dialog, which would break the flow). Repeat on the Utkal University **Check Results** form.
- [ ] Navigate to `/admin/` → tenant list renders → click **Scan WCAG** on any tenant → report appears. Open DevTools → Network: confirm `axe.min.js` served from the same origin (starts with `/admin/vendor/`). No request to `cdn.jsdelivr.net` — the offline bundle ships axe v4.11.3 in `apps/admin/vendor/axe.min.js`.

### TTS-outage path

Meta MMS-TTS is the single TTS engine — there is no browser-voice
fallback. The check here is that an outage surfaces a clean error
instead of hanging the widget.

- [ ] Leave the demo running. Open Task Manager → End `aaas-tts.exe`.
- [ ] Click **Read this page** again. Status pill should flip to `TTS unavailable — check the gateway` in red, and nothing should play.
- [ ] Close the browser, kill `aaas-gateway.exe` from Task Manager, close the launcher window. Open a fresh launcher and `start.bat` again — everything comes back.

### Port-conflict path

- [ ] In a terminal, run `python -m http.server 8000` to squat on the gateway's default port. (Or: open anything else on 8000.)
- [ ] Run `start.bat` again. Watch the launcher window — it should log `gateway port 8000 busy -> using 8001` (or similar), then still succeed. The four services all auto-pick alternates if 8000/8001/8002/8003 are busy.
- [ ] Kill the squatting server, close everything, rerun clean.

### Offline path

- [ ] Disable Wi-Fi *and* disconnect Ethernet. (Do this while the services are already stopped.)
- [ ] Run `start.bat`. Demo must still work end-to-end — the entire bundle is offline.

### Cleanup path

- [ ] Close the launcher window with **any key** (not the X button in the corner).
- [ ] Check Task Manager: no `aaas-tts.exe` or `aaas-gateway.exe` zombies.
- [ ] Re-run `start.bat` clean — should take less time than the first run (caches warm).

## Logs sanity check

After a successful run, inside `AaaS-Demo/logs/`:

- [ ] `tts.log` has a `model cache: ...\\models` line and no ERROR-level entries.
- [ ] `stt.log` and `translate.log` each log a `started on http://127.0.0.1:<port>` and nothing else noisy.
- [ ] `gateway.log` shows `http://127.0.0.1:<port>` listening, no traceback.
- [ ] File sizes reasonable (<1 MB each) — if they are empty, the exes did not start from the launcher and you were looking at a false success.

## Hackathon-day pre-flight

30 minutes before judging, on the **actual presenter laptop**:

- [ ] Plug in the USB. Copy `AaaS-Demo/` to Desktop.
- [ ] Run `start.bat` end-to-end. Verify Odia audio plays.
- [ ] Close the launcher. Leave the folder on the Desktop but do *not* leave services running (they eat battery and one of the demo jokes is the cold start).
- [ ] Have the backup USB stick in a pocket, not in the laptop bag.
- [ ] Have `PITCH/AaaS.pdf` open on the laptop's PDF reader as a second fallback.
- [ ] Know which browser the laptop defaults to. Browser choice no longer affects voice quality — Meta MMS-TTS is the sole engine — but Edge/Chrome remain the primary targets for injection-world compatibility.

## Red-flag aborts

If any of these appear in rehearsal, **rebuild the bundle on the dev machine**
and run the whole checklist again — do not patch on the target laptop:

- Any Python traceback in the launcher window.
- `BUNDLE UNVERIFIED — DO NOT SHIP` in the build log.
- First synth >10 seconds after prewarm has completed.
- Browser opens but the ଅ button is missing (widget not loaded — gateway serving the wrong assets).
- Any 502/504 from the gateway after `/readyz` has returned 200.

## If it fails live

1. Close the browser and the launcher window.
2. Re-run `start.bat`. 90% of transient issues resolve on a second start.
3. If still broken, pivot to the deck. Slides 5-8 describe the architecture; you can walk judges through the tech story without a working demo. Promise a follow-up video and note any judge email addresses offered.

Team SUBARNAREKHA — you've rehearsed this. Trust the bundle.
