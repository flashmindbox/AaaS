# AaaS Companion browser extension

An MV3 Chromium extension that injects the AaaS accessibility widget
into **any** web page. This doc is for maintainers. End-user install
instructions live in [`apps/extension/README.md`](../apps/extension/README.md)
and are also shipped in the judge-laptop bundle as `EXTENSION-README.txt`.

## Why the extension is the demo's "wow" moment

The widget-as-script-tag story requires site-owner cooperation. Every
institution has to paste a line of HTML. The extension flips the
integration model: the **user** decides to install, and gains the same
accessibility features on every site they visit — including sites that
have never heard of AaaS.

For the pitch, that means:

> "Imagine a dyslexic first-year student at Utkal University. She
> installs AaaS Companion once. Then — on her admission portal, on the
> BSE result page, on the Odisha State Pension portal her parents
> use — the same ଅ button appears. Same voice. Same dyslexia mode.
> Same Odia. Zero cooperation required from any of those sites."

The three demo portals in the bundle still show the *native* integration
path (one `<script>` tag in the page HTML). The extension shows the
*universal* integration path. Both run off the same widget code.

## Repo layout

```
apps/extension/
├── manifest.json          # MV3 manifest
├── background.js          # service worker, seeds chrome.storage defaults
├── inject-config.js       # isolated-world bridge, runs at document_start
├── widget.js              # COPY of apps/widget/dist/widget.js
├── ondevice.js            # lazy backend for on-device TTS/STT (v0.2.0)
├── popup.html             # toolbar popup markup
├── popup.css              # popup styling
├── popup.js               # popup controller (load/save/test)
├── icons/                 # 16/32/48/128 PNG (branded "ଅ" if Pillow+font)
├── vendor/                # transformers.js + ort-web WASM (gitignored)
├── models/                # ONNX weights: mms-tts-{ory,hin,eng} + whisper-base (gitignored)
├── README.md              # end-user-facing install doc
└── (no build output — the folder IS the extension)
```

## The cross-world config bridge

MV3 distinguishes two JS worlds inside a tab:

- **Isolated world.** The world content scripts run in by default. Has
  access to `chrome.*` APIs, but its `window` is a different JS context
  from the page's — globals aren't visible to page scripts.
- **Main world.** The page's own JS context. No `chrome.*` APIs, but
  `window.*` is shared with the page.

The widget needs the **main world** — it manipulates `document.body`,
Shadow DOM, plays server-returned TTS audio via `<audio>`, and listens
to page events. But the gateway URL and API key live in
`chrome.storage.sync`, which is only reachable from the **isolated
world**.

Solution: two content scripts, the DOM as the bridge.

1. `inject-config.js` (isolated, `run_at: "document_start"`) reads
   `chrome.storage.sync.get({gateway, apiKey, defaultLang, enabled})`
   and writes the values onto `document.documentElement.dataset` —
   e.g. `data-aaas-gateway`, `data-aaas-key`, `data-aaas-lang`. The
   DOM is shared across worlds, so the attributes are visible to the
   main world.

2. `widget.js` (main world, `run_at: "document_idle"`) has a config
   resolution chain that now includes a third lookup:

   ```js
   CURRENT_SCRIPT?.dataset.gateway      // native script-tag embed
     || window.AAAS_GATEWAY_URL          // page-global override
     || HTML_DATASET.aaasGateway         // extension bridge ← NEW
     || SCRIPT_ORIGIN
     || "http://127.0.0.1:8000"
   ```

   Same chain for `apiKey`. Backward compatible — script-tag embeds
   still win via `CURRENT_SCRIPT.dataset`.

`run_at: "document_idle"` (not `"document_end"`) is deliberate — by
that point the page has finished parsing and most DOM manipulations
the page's own scripts will do are done, so the widget's Shadow DOM
host is less likely to get reparented.

## CORS on the gateway

The extension's widget runs in the page's main world, so fetches carry
the page's origin (`https://odisha.gov.in`, etc). The gateway sits at
`http://127.0.0.1:8000` — a different origin. Without CORS, the
browser blocks the preflight OPTIONS.

Fix: `services/gateway/app/main.py` adds FastAPI's `CORSMiddleware`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
    max_age=600,
)
```

Safe to use `*` because we don't accept cookies — auth is via the
`X-API-Key` header which is passed through explicitly. Credentials
stay `False`, which also keeps the wildcard origin legal under the
CORS spec.

Mixed-content note: browsers *do* let an HTTPS page fetch
`http://127.0.0.1:*` because localhost is a "potentially trustworthy"
origin under the Secure Contexts spec. So the HTTPS→localhost path
works out of the box for the USB demo.

## On-device mode (v0.2.0)

The popup's "On-device mode" toggle flips the widget to an entirely
offline speech stack: Meta MMS-TTS (Odia / Hindi / English) and
OpenAI Whisper-base both run inside the page via transformers.js +
onnxruntime-web. Translation still goes through the gateway — IndicTrans2
(~2 GB for both directions) is too heavy to bundle for v1.

### Data flow when on-device is active

```
popup toggle ──► chrome.storage.sync.onDevice = true
                      │
                      ▼
inject-config.js (isolated, document_start)
  reads chrome.storage.sync, chrome.runtime.getURL("")
  writes:  html.dataset.aaasOnDevice = "1"
           html.dataset.aaasExtRoot = "chrome-extension://<id>/"
                      │
                      ▼
widget.js (main world, document_idle)
  sees ON_DEVICE = true
  first call to synthesise(): dynamic import(EXT_ROOT + "ondevice.js")
                      │
                      ▼
ondevice.js (main world, ESM)
  import(EXT_ROOT + "vendor/transformers.min.js")
  env.localModelPath = EXT_ROOT + "models/"
  env.backends.onnx.wasm.wasmPaths = EXT_ROOT + "vendor/"
  pipeline("text-to-speech", "mms-tts-ory", { dtype: "q8" })
  → Float32Array → WAV Blob → <audio>
```

Failures in the on-device path fall back to the gateway without the
user seeing anything — both paths emit Meta MMS-TTS audio, so the
voice is consistent. (Memory note: MMS-TTS is the *only* sanctioned
TTS family for this repo; in-browser and server both use the same
`facebook/mms-tts-{ory,hin,eng}` checkpoints, just different
runtimes.)

### CSP

MV3 blocks WebAssembly by default. The manifest declares:

```json
"content_security_policy": {
  "extension_pages": "script-src 'self' 'wasm-unsafe-eval'; object-src 'self';"
}
```

`'wasm-unsafe-eval'` enables ort-web's JIT compilation of
WebAssembly modules. `'self'` forces every script + model URL to
resolve inside the extension — any CDN dependency (jsdelivr, unpkg)
is rejected. That's why `vendor/` ships the transformers.js bundle
and ort-web WASM binaries locally rather than loading them from a
CDN at runtime.

### Size budget

| Layer               | Size   | Notes                                  |
|---------------------|--------|----------------------------------------|
| transformers.js     | ~2 MB  | `vendor/transformers.min.js`           |
| ort-web WASM (×2)   | ~18 MB | jsep + non-jsep builds, ort-web picks  |
| mms-tts-ory (int8)  | ~50 MB | Converted here — no Xenova release     |
| mms-tts-hin (int8)  | ~40 MB | `Xenova/mms-tts-hin`                   |
| mms-tts-eng (int8)  | ~40 MB | `Xenova/mms-tts-eng`                   |
| whisper-base (int8) | ~80 MB | `Xenova/whisper-base`                  |
| **Total**           | ~230 MB| sideload only, not Chrome Web Store    |

IndicTrans2 (the translation model) adds another ~2 GB for the two
directions, which is why it's out of scope for v1.

### Rebuilding models + vendor

```powershell
# Vendor transformers.js + ort-web (needs network to jsdelivr):
python scripts/build_extension_vendor.py

# Download + convert ONNX models (needs huggingface-hub + optimum + torch):
pip install huggingface-hub optimum[onnxruntime] transformers torch sentencepiece
python scripts/build_extension_models.py

# Full bundle rebuild (calls both of the above automatically):
python scripts/build_bundle.py
```

The Odia conversion (`facebook/mms-tts-ory` → ONNX int8) is the only
non-trivial step: optimum's VITS exporter occasionally fails because
the task name changed from `text-to-speech` to `text-to-audio` across
releases. The script retries both. If both fail, the zip still
builds — just without Odia on-device support, and on-device Odia
falls back to gateway Odia.

## Build integration

`scripts/build_bundle.py`'s `build_extension()` step:

```python
def build_extension() -> Path:
    # 1. Refresh apps/extension/widget.js from apps/widget/dist/widget.js
    # 2. Re-run scripts/build_extension_icons.py (stdlib + Pillow fallback)
    # 3. scripts/build_extension_vendor.py  (hard-fail on network issue)
    # 4. scripts/build_extension_models.py  (soft-fail — gateway path stays OK)
    # 5. Sanity-check every manifest-referenced file exists
    # 6. Zip apps/extension/ -> dist/AaaS-Extension.zip (~230 MB with on-device)
```

Called from `main()` right after `build_widget_bundle()`, so the
extension is always in sync with the widget. `assemble()` copies
`apps/extension/` into `dist/AaaS-Demo/extension/` for sideload from
the USB stick.

Icon rendering tries Pillow + the Noto Sans Oriya subset font first
(produces the white-on-blue "ଅ"). Falls back to a stdlib-only
blue-square-with-white-circle PNG if either is missing — good enough
for a functional toolbar icon even on a minimal Python install.

## Compatibility matrix

| Engine    | Min version | MAIN-world content scripts | Status    |
|-----------|-------------|---------------------------|-----------|
| Chrome    | 111         | Yes                       | Supported |
| Edge      | 111         | Yes (Chromium)            | Supported |
| Brave     | 1.50        | Yes (Chromium 111)        | Supported |
| Opera     | 97          | Yes (Chromium 111)        | Supported |
| Firefox   | 128         | Yes                       | Untested  |
| Safari    | 16.4+       | Limited                   | Not yet   |

The demo script targets Edge on the judge laptop (pre-installed on
Windows 10/11) — no install step, no Chrome account required.

## Not shipped yet

- Per-tab enable/disable toggle (requires action-click messaging).
- Context-menu "Read selection aloud" (stop-gap idea; TTS path already
  supports arbitrary text).
- Firefox / Safari packaging variants.
- Chrome Web Store listing — the review queue is ~1 week, which beats
  the hackathon window. Sideload is the correct distribution for the
  demo; store is a Phase 2 polish item.
- Keyboard shortcut (`Alt+A`) to open the panel from the keyboard.
- Signed `.crx` for one-click install.

## Changing defaults

Seed values live in three places that must stay in sync:

- `apps/extension/inject-config.js` — `defaults = { gateway, apiKey, onDevice, ... }`
- `apps/extension/background.js`    — `DEFAULTS = { gateway, apiKey, onDevice, ... }`
- `apps/extension/popup.js`         — `DEFAULTS = { gateway, apiKey, onDevice, ... }`

If you change one, change all three. (Not worth DRYing into a shared
JS module for three small objects — the content scripts run in
different worlds and can't easily share imports without a build step,
and the extension is deliberately zero-build-tools.)
