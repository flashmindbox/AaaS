AaaS Accessibility Companion — Browser Extension
=================================================

This USB bundle ships a Chrome/Edge browser extension that injects the
AaaS accessibility widget into ANY website you visit — not just the
three demo portals in this bundle.

Why that matters
----------------
The widget on its own is a <script> tag. Without this extension, it
only works on sites whose operators have integrated AaaS. With this
extension installed, a blind / dyslexic / non-English-literate user
can use the same accessibility features on any page they open —
government portals, news sites, university admission pages — without
the site doing anything at all.


Install (Chrome / Edge / Brave)
-------------------------------
1. Start the AaaS services on this laptop:
     double-click  start.bat
   Wait for the "All services ready" line; keep the window open.

2. Open your browser and go to:
     chrome://extensions   (Chrome / Brave)
     edge://extensions     (Edge)

3. Turn on "Developer mode" (top-right toggle).

4. Click "Load unpacked".

5. Select this folder:
     .\extension\

   The AaaS Companion icon (blue square with a white dot) appears in
   your browser toolbar.

6. Click the icon once to open the settings popup. Defaults are already
   correct for the USB bundle — just click "Test gateway" to confirm
   the services are reachable, then "Save".

7. Visit any website. Look for the round ଅ button in the bottom-right
   corner. Click it to open the accessibility panel.


Demo walkthrough for judges
---------------------------
  (a) Open  https://odisha.gov.in/  in the browser.
      -> Click the ଅ button.
      -> Click "Read this page" — the page is read aloud in Odia.

  (b) Open  https://www.india.gov.in/  (or even https://en.wikipedia.org/)
      -> Same ଅ button.
      -> Keep language on Odia, click Read — the English content is
         translated to Odia (Google Translate) and spoken in the Odia
         voice. Works on strict sites like Wikipedia too, because the
         voices run on-device and translation goes through the extension's
         background, not the page.
      -> Or click "Translate this page" to flip the whole page to Odia
         in place.

  (c) Open any form page (e.g. a search box).
      -> Click ଅ, then "Speak (fill by voice)".
      -> Speak in Odia / Hindi / English.
      -> The transcript appears in the panel; sites that integrate
         with AaaS auto-fill the active field.

  (d) Turn on "Dyslexia mode" — the whole page reflows with
      Odia-aware conjunct-safe spacing.


Uninstall
---------
  chrome://extensions  ->  Remove.


If something goes wrong
-----------------------
- The ଅ button doesn't appear?
  Reload the tab. The content script only runs on pages loaded while
  the extension was installed.

- "Gateway unreachable"?
  Not fatal. The read-aloud voices run ON-DEVICE (in the browser), and
  translation uses Google Translate, so neither needs start.bat. The
  gateway is only used for voice-to-text (Speak), the bundled demo
  portals, and as an OFFLINE translation fallback. If you want those,
  make sure start.bat is still running — the popup's "Test gateway"
  button probes  http://127.0.0.1:8000/healthz .

- "Translate this page" does nothing?
  That feature needs an internet connection (it uses Google Translate).
  Read-aloud and the on-device voices still work without internet.

- Audio plays in the wrong voice?
  Check the "Default language" in the popup, or the page's own
  <html lang="..."> attribute. Use the panel's Language dropdown to
  force a specific voice.

- A particular site blocks the widget?
  The voices run on-device and translation goes through the background,
  so read-aloud works even on strict-CSP sites (e.g. Wikipedia). A very
  small number of sites block ALL extension injection — there the ଅ
  button won't appear at all; just try another page.


Files
-----
  extension/manifest.json     MV3 manifest
  extension/background.js     Service worker (defaults + Google Translate proxy)
  extension/inject-config.js  Isolated-world config + translate bridge
  extension/widget.js         The widget itself (bundled copy)
  extension/ondevice.js       On-device TTS/STT (transformers.js + ONNX)
  extension/models/, vendor/  On-device voice models + WASM runtime
  extension/popup.html/css/js Toolbar popup
  extension/icons/            PNG icons (16/32/48/128)

  AaaS-Extension.zip          Zipped extension (under dist/ in the
                              source repo). Same contents as the
                              unpacked folder above.
