======================================================================
  AaaS  -  Accessibility as a Service
  Team SUBARNAREKHA   |   Smart Odisha Hackathon 2025
  One-page survival guide for the judge-laptop demo
======================================================================


HOW TO RUN THE DEMO
-------------------
  1. Copy the entire "AaaS-Demo" folder to the laptop (Desktop is fine).
  2. Double-click  start.bat
  3. Wait until a browser window opens at the Jajpur demo page
     (usually 30-90 seconds the first time - four services start up).
  4. Click the round  ଅ  button at the bottom-right of the page,
     then click "Read this page".
  5. When you are done, press any key in the launcher window to stop
     the services cleanly.

That is the whole demo. Everything below is ONLY if something goes
wrong.


OPTIONAL BUT HIGH-IMPACT:  INSTALL THE BROWSER EXTENSION
--------------------------------------------------------
The bundle ships a Chrome / Edge extension that injects the AaaS widget
into ANY website you visit - not just our three demo portals. This is
the single strongest demo moment for judges:

  1. Make sure start.bat is still running.
  2. Open Edge (or Chrome) and go to:  edge://extensions
  3. Turn on "Developer mode" (top-right toggle).
  4. Click "Load unpacked".
  5. Select the  extension\  folder next to this README.
  6. Visit  https://odisha.gov.in/  (or any website).
  7. The round ଅ button appears at the bottom-right of every page.
  8. Click it, then "Read this page" - a live Odisha government
     website reads itself aloud in Odia.

Full instructions in  EXTENSION-README.txt.


WHAT IS RUNNING?
----------------
The bundle starts four services on localhost:

    Gateway     http://127.0.0.1:8000   (proxy + static frontends)
    TTS         http://127.0.0.1:8001   (Odia speech synthesis)
    STT         http://127.0.0.1:8002   (speech-to-text, mock engine)
    Translate   http://127.0.0.1:8003   (Indic <-> English, mock)

If any of 8000-8003 is busy, the launcher picks the next free port
above each and the browser URL adjusts automatically.


IF WINDOWS SHOWS A BLUE "WINDOWS PROTECTED YOUR PC" SCREEN
----------------------------------------------------------
That is SmartScreen. It fires on unsigned software. This bundle is
not signed (code-signing costs money and takes weeks - out of scope
for a hackathon).

  -> Click "More info"
  -> Click "Run anyway"

You will only see this once per machine.


IF WINDOWS DEFENDER DELETES OR QUARANTINES A FILE
-------------------------------------------------
PyInstaller-packaged Python executables sometimes trip Defender's
heuristics. Symptom: one of the aaas-*.exe files vanishes from the
services\ folder a few seconds after you extract the bundle, or the
launcher reports "ERROR: services did not start in time".

  -> Open "Windows Security"
  -> "Virus & threat protection"
  -> "Manage settings" under "Virus & threat protection settings"
  -> "Add or remove exclusions"
  -> Add the AaaS-Demo folder as an exclusion
  -> Re-extract the bundle from the USB

Then double-click start.bat again.


IF THE LAUNCHER SAYS "No free port near 8000/8001/8002/8003"
------------------------------------------------------------
Something on the laptop is holding ports 8000-8050 AND 8001-8051 AND
8002-8052 AND 8003-8053 (very unusual).  Close any of: Zoom, Skype,
Docker Desktop, Jupyter, node dev servers. Then re-run start.bat.


IF THE BROWSER DOES NOT OPEN BY ITSELF
--------------------------------------
The launcher prints the URL on its own line ("Demo is LIVE at ...").
Copy that URL and paste it into any browser.


"TTS UNAVAILABLE" APPEARS IN RED UNDER THE BUTTONS  -  WHAT DOES IT MEAN?
-------------------------------------------------------------------------
It means the Odia neural TTS service on the laptop is not reachable,
so the widget cannot read the page. Meta MMS-TTS is the only engine
the widget uses - there is NO browser-voice fallback. Nothing will
speak until the TTS service is back up.

To recover, close the launcher window and double-click start.bat
again. When the launcher prints "tts ready" and "prewarm ok or ...",
click "Read this page" once more.


MANUAL START  -  LAST RESORT ONLY
---------------------------------
If start.bat misbehaves you can launch the services by hand. Open
four terminals in the AaaS-Demo folder:

    Terminal 1:  services\aaas-tts\aaas-tts.exe
    Terminal 2:  services\aaas-stt\aaas-stt.exe
    Terminal 3:  services\aaas-translate\aaas-translate.exe
    Terminal 4:  set UPSTREAM_TTS_URL=http://127.0.0.1:8001
                 set UPSTREAM_STT_URL=http://127.0.0.1:8002
                 set UPSTREAM_TRANSLATE_URL=http://127.0.0.1:8003
                 services\aaas-gateway\aaas-gateway.exe

Then open  http://127.0.0.1:8000/demo/jajpur-collectorate/  manually.

To stop, Ctrl+C each terminal. If any refuses, open one more and run:
  taskkill /f /im aaas-tts.exe /im aaas-stt.exe ^
           /im aaas-translate.exe /im aaas-gateway.exe


WHERE ARE THE LOGS?
-------------------
Look inside the logs\ folder next to start.bat:

  logs\tts.log        - TTS service output (model load, synthesis)
  logs\stt.log        - STT service output (mock engine)
  logs\translate.log  - Translate service output (mock engine)
  logs\gateway.log    - Gateway output (HTTP access, errors)

If something fails, zip the logs\ folder before you reboot - it has
the evidence.


EMERGENCY CONTACT
-----------------
If the demo is in 2 minutes and the bundle is broken, skip the
bundle entirely and go to the fallback slide:
  - Open the deck  PITCH\AaaS.pdf
  - Speak to slides 5-8 which already describe the architecture
  - Promise the judges a live walk-through after the session

Team SUBARNAREKHA has got this. Good luck.
======================================================================
