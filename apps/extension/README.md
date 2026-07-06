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
3. Click → panel with:
   - **Read this page** (Meta MMS-TTS — no browser-voice fallback)
   - **Speak (fill by voice)** (dispatches `aaas-transcript` event)
   - **Navigate by voice** (Alt+V) — speak a command or a link name in
     Odia/Hindi/English; the widget matches it against the page's links
     and buttons (built-in Odia→English nav glossary + translation),
     highlights the winner, announces it, then clicks. Refuses and
     lists candidates when it isn't confident. Scriptable without a
     mic via the `aaas-voice-command` CustomEvent.
   - **Translate this page** (in-place; IndicTrans2 via gateway,
     Google fallback)
   - **Easy Read this page** — rule-based plain-language rewriting of
     the whole page (legalese → everyday words, long sentences split)
     **in the page's current language**: an English page stays English,
     a translated-to-Odia page gets the Odia rules. Composes with
     Translate (translate first, then Easy Read → simple Odia).
     **Needs the gateway** — no Google fallback for this.
   - **Read a document to me** — the widget finds the scanned images
     and PDF links on the page itself: one document goes straight to
     processing, several open a big plain-language chooser (hovering a
     row highlights the document on the page), none offers a
     point-at-it fallback. The document goes through the gateway's
     Tesseract OCR, then simplify + translate, and the result appears
     large-print in a centered modal that **starts reading aloud
     automatically**. **Needs the gateway.** Same-origin documents work
     (the normal government-portal case); cross-origin CDN images may
     be blocked by the page's CORS.
   - **Language picker** (Auto / Odia / Hindi / English)
   - **Dyslexia mode** toggle — bundles Atkinson Hyperlegible (Latin
     subset, base64-inlined) so the font swap works on any machine;
     letter-spacing applies to Latin text only and is explicitly reset
     on Odia/Hindi subtrees (conjunct-safe).
   - **Reading ruler** toggle — a line-focus band that follows the
     pointer (and keyboard focus), dimming everything outside it.
4. **Translation uses Google Translate** by default. The widget runs in
   the page's MAIN world (no cross-origin access), so requests are relayed
   through the background service worker — the one context that can call
   Google regardless of the page's CSP/CORS. This means read-aloud in
   Odia/Hindi and "Translate this page" work on **any** website with no
   local gateway running. When the local gateway is reachable, translation
   prefers its `/translate` (IndicTrans2) for the best Odia quality.
5. **On-device mode (default ON):** TTS and STT run entirely inside the
   browser via WebAssembly (Meta MMS-TTS voices, incl. Odia). Combined
   with Google Translate above, the full feature set works with no backend
   at all. Flip it off in the popup to route TTS/STT to the gateway
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
- **Translation:** the gateway's IndicTrans2 when reachable, otherwise
  Google Translate (via the background worker). No setting required.
- **Gateway URL:** `http://127.0.0.1:8000`
  Only needed for the fallback paths: TTS/STT when on-device mode is off,
  and translation when Google is unreachable. Point it at wherever AaaS
  is running (USB bundle, OCAC cloud deploy, Docker compose stack, etc.).
- **API key:** seed demo key. Replace with a real tenant key in
  production.
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
| `background.js`   | Service worker — seeds defaults + Google Translate proxy |
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
