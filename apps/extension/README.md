# AaaS Companion — Browser Extension

A Chromium (Chrome / Edge / Brave) MV3 extension that injects the AaaS
accessibility widget into **any** web page. No cooperation from the site
owner required — a disabled user installs the extension once, then every
page they visit gains read-aloud, dictation, translation, and
dyslexia-friendly rendering in Odia / Hindi / English.

## Why this exists

The widget on its own is a `<script>` tag. It only works on sites whose
owners have integrated AaaS. That doesn't help a blind Odia-speaking
citizen who just wants to read `india.gov.in` or `odisha.gov.in` out
loud today.

The extension solves the reach problem: **the user controls integration,
not the site owner.**

## What it does

On every page you visit, the extension:

1. Injects `widget.js` into the page's main world (MV3 `world: "MAIN"`).
2. Widget paints a floating ଅ button in the bottom-right corner.
3. Click → icon-grid panel (Odia-first labels) with six tiles:
   - **ପଢ଼ି ଶୁଣାଅ · Read aloud** (Meta MMS-TTS — no browser-voice
     fallback). Highlights each block as it's spoken; ⏮/⏭ buttons (and
     ←/→ keys) replay or skip a section, Space pauses, Esc stops.
   - **ଅନୁବାଦ · Translate → Odia** — whole-page in-place translation
     (IndicTrans2 via the gateway), with a one-tap ↺ undo
     on the tile.
   - **ସହଜ ପଢ଼ା · Easy Read** — rule-based plain-language rewriting of
     the whole page (legalese → everyday words, long sentences split)
     **in the page's current language**: an English page stays English,
     a translated-to-Odia page gets the Odia rules. ↺ undo. Composes
     with Translate. **Needs the gateway.**
   - **ଦଲିଲ ପଢ଼ · Read document** — finds the scanned images and PDF
     links on the page and always asks which one to read. The document
     goes through the gateway's Tesseract OCR, then simplify +
     translate, and opens **side by side**: the original page images on
     the left, the text on the right, reading aloud automatically with
     an amber highlight following the voice across pages. ⛶ maximizes.
     **Needs the gateway.** Same-origin documents work (the normal
     government-portal case); cross-origin CDN images may be blocked by
     the page's CORS.
   - **କହି ଲେଖ · Speak to fill** — with a field focused, dictates into
     that field. With nothing focused, **guided form fill**: walks every
     empty field, speaks its label aloud, beeps, listens, writes the
     answer, and moves on — with a progress counter and one automatic
     retry for numbers. Odia names/addresses are **transliterated to
     Latin letters** (Purnnachandra, never "full moon"); spoken numbers
     become digits (Odia words, phonetic English, "double" forms, tens
     words for ages); emails assemble from spoken at/dot. It never
     presses Submit — it parks focus on the button and leaves the
     decision to the user. Esc cancels.
   - **କହି ଚଲାଅ · Voice command** (Alt+V) — speak a command or a link
     name in Odia/Hindi/English. Matching survives real sites: English
     link names heard phonetically through the Odia STT ("କଣ୍ଟାକ୍ଟ" →
     Contact) are romanized and sound-matched; Odia names match across
     matra/virama slips; links hidden in carousels and dropdown menus
     are reachable; duplicate header/footer links count as one. When
     not confident it shows the top candidates as **tappable buttons**
     instead of an error. Scriptable without a mic via the
     `aaas-voice-command` CustomEvent.
   - **Language picker** (Auto / Odia / Hindi / English) and a
     **Reading comfort** section:
     - **ଆରାମ ଅକ୍ଷର · Comfortable letters** — bundles **OpenDyslexic**
       (regular + bold, base64-inlined; Atkinson Hyperlegible as
       fallback) so the font swap works on any machine; letter-spacing
       applies to Latin text only and is explicitly reset on Odia/Hindi
       subtrees (conjunct-safe).
     - **ପଢ଼ା ରେଖା · Reading ruler** — a line-focus band that follows
       the pointer (and keyboard focus), dimming everything outside it.
     - **ଛୁଇଁଲେ କୁହେ · Hover to speak** — speaks what you point at;
       selecting text reads the selection.
     - A **keyboard-shortcuts overlay** (press ? with the panel open).
4. **Translation uses the AaaS gateway** (IndicTrans2). The widget runs
   in the page's MAIN world, so on strict-CSP sites its direct fetch is
   blocked; those requests are relayed through the background service
   worker, which reaches the gateway regardless of the page's CSP. This
   means "Translate this page" works on **any** website. There is no
   third-party translation fallback.
5. **On-device mode (default ON):** TTS and STT run entirely inside the
   browser via WebAssembly (Meta MMS-TTS voices, incl. Odia). Combined
   with gateway translation above, the full feature set works on any site.
   Flip it off in the popup to route TTS/STT to the gateway
   instead. Models add ~230 MB to the extension on first install.

## Installing (unpacked, for judges and testers)

1. Open `chrome://extensions` (or `edge://extensions`, `brave://extensions`).
2. Turn on **Developer mode** (top-right toggle).
3. Click **Load unpacked**.
4. Select either:
   - `dist/AaaS-Demo/extension/` after running `scripts/build_bundle.py`, or
   - `apps/extension/` directly from this repo.
5. The ଅ icon appears in the toolbar. Click it → popup with settings.

## First-run settings

The popup opens automatically after install. Defaults:

- **Enabled on all pages:** on. Toggle off to disable everywhere without
  uninstalling.
- **On-device mode:** on. TTS and STT run in WebAssembly inside the
  page — no gateway needed. First utterance in each language warms up
  the ONNX model (~2 s lag); subsequent ones are sub-second. Turn it
  off to route TTS/STT to the gateway instead.
- **Translation:** the gateway's IndicTrans2 (via the background worker on
  strict-CSP pages). No setting required.
- **Gateway URL:** `https://168-144-216-83.sslip.io` (hosted; use `http://127.0.0.1:8000` for the offline USB bundle)
  Used for translation, Easy Read and document OCR, and for TTS/STT when
  on-device mode is off. Point it at wherever AaaS
  is running (USB bundle, OCAC cloud deploy, Docker compose stack, etc.).
- **API key:** the `aaas-companion` tenant's key (not an operator key).
  The gateway only accepts it when `EXTENSION_API_KEY` is set to the same
  value; rotate both together.
- **Default language:** `auto` — the widget uses the page's `lang`
  attribute. Override for sites with missing / wrong lang tags.

Click **Test gateway** to probe `/healthz` before saving.
Click **Save**, then reload any open tab to apply.

## Compatibility

- Chrome 111+ (for `content_scripts.world: "MAIN"`)
- Edge 111+
- Brave, Opera, Vivaldi — anything Chromium 111+
- Firefox 128+ (MV3 main-world support; untested)

## Known limits

- **Strict CSP pages.** A handful of sites (some banks, certain `.gov`
  portals) block inline audio or dynamic resource loads even from
  extensions. TTS playback may fail on those — the widget shows a TTS
  error in the status pill; there is no browser-voice fallback.
- **Mixed content.** Fetches from an `https://` page to
  `http://127.0.0.1:8000` are allowed because the browser treats
  localhost as a secure context. If you host the gateway on a non-local
  HTTP server, HTTPS pages will block those fetches — use HTTPS for
  the gateway in that case.
- **Microphone access (STT).** `getUserMedia` requires a secure context
  — HTTPS pages work, rare HTTP pages don't. TTS/translation still work
  on HTTP pages.
- **Iframes.** Disabled for now (`all_frames: false` in the manifest).
  The FAB appears once per top-level page.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Any website (e.g. https://odisha.gov.in)                       │
│                                                                  │
│  ┌──── ISOLATED world ────┐   ┌──── MAIN world ─────────────┐  │
│  │  inject-config.js      │   │  widget.js                   │  │
│  │  (document_start)      │   │  (document_idle)             │  │
│  │                        │   │                              │  │
│  │  chrome.storage.sync   │   │  reads document.documentEl.  │  │
│  │    .get(defaults)      │   │    dataset.aaasGateway       │  │
│  │                        │   │    dataset.aaasKey           │  │
│  │  html.dataset.aaas* =  │   │                              │  │
│  │    { gateway, key }    │   │  fetch(gateway + "/tts/...") │  │
│  └────────┬───────────────┘   └──────────┬───────────────────┘  │
│           │  DOM (shared between worlds) │                      │
│           └────────────┬───────┬─────────┘                      │
│                        ▼       ▼                                │
│             <html data-aaas-gateway="..." data-aaas-key="...">  │
└───────────────────────────────────┬─────────────────────────────┘
                                    │  cross-origin POST
                                    ▼
                        ┌───────────────────────┐
                        │  AaaS Gateway         │
                        │  (localhost or cloud) │
                        │  CORS: allow *        │
                        │  /tts /stt /translate │
                        └───────────────────────┘
```

The two content scripts bridge via the shared DOM (data attributes on
`<html>`) because chrome.storage is only available in the isolated
world, but the widget needs to run in the main world to be a peer of
the page's own scripts.

## Files

| File              | Purpose                                      |
|-------------------|----------------------------------------------|
| `manifest.json`   | MV3 manifest, permissions, content scripts, CSP for WASM |
| `background.js`   | Service worker — seeds defaults + gateway translate proxy |
| `inject-config.js`| Isolated-world bridge → dataset on `<html>` + translate relay |
| `widget.js`       | The widget itself (copied from `apps/widget/dist/`) |
| `ondevice.js`     | Lazy-loaded adapter: transformers.js + ONNX for offline TTS/STT |
| `popup.html/.css/.js` | Toolbar popup for gateway URL + API key + on-device toggle |
| `icons/`          | 16/32/48/128 PNG icons                       |
| `vendor/`         | transformers.js + ort-web WASM (build product, ~20 MB) |
| `models/`         | ONNX model weights for on-device mode (build product, ~210 MB) |

## Rebuilding

```powershell
# Widget source change → rebuild widget.js + extension copy
python scripts/build_widget.py
python scripts/build_extension_icons.py   # optional, idempotent

# Fetch transformers.js + ort-web (needs internet the first time):
python scripts/build_extension_vendor.py

# Download + convert ONNX models (~230 MB, 5-10 min first run):
pip install huggingface-hub optimum[onnxruntime] transformers torch sentencepiece
python scripts/build_extension_models.py

# Full USB bundle build — calls all of the above automatically:
python scripts/build_bundle.py
```

The extension's `widget.js` is overwritten from
`apps/widget/dist/widget.js` by **both** `scripts/build_widget.py` and
`scripts/build_bundle.py`, so only edit the widget source
(`apps/widget/src/widget.js`) — never the copy under `apps/extension/`.
After a rebuild, hit ↻ on the extension card in `chrome://extensions`
to pick up the new file.

`vendor/` and `models/` are gitignored because they're build products
(~230 MB). A fresh clone ships a gateway-only extension until those
scripts run.
