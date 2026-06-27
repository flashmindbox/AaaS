AaaS Portable — Update (2026-04-24)
===================================

*** Start here: open UPDATE-GUIDE.pdf in this zip ***
The PDF is a 4-page illustrated walkthrough with numbered steps,
expected output screenshots, a verification checklist, and a
troubleshooting section. It's the easiest way to update.

This plain-text file is the same information in condensed form, if
you prefer reading terminals over PDFs.

-------------------------------------------------------------------

This is a patch update. It updates the accessibility widget AND adds
a new auto-heal system that re-downloads any missing AI models. You
don't need to re-run SETUP-FRIEND.bat from scratch — but the updated
SETUP-FRIEND.bat in this zip will run the new auto-heal check if you
DO re-run it.


What's new
----------

Widget fixes:
* Odia: long paragraphs stream sentence-by-sentence — first audio in
  ~1 second instead of waiting for the whole paragraph.
* Mic flow: speaking Odia fills ENGLISH into form fields. Odia /
  Devanagari digits are auto-converted to ASCII (2025 from ୨୦୨୫).
* Translation safety: if translate can't render English, form stays
  empty with a red error — no more silent Odia-in-English-form.
* Hover-to-speak now speaks the VISIBLE text, not hidden aria-label.
  Icon buttons still fall back to aria-label correctly.
* DevTools shows [AaaS/hover] diagnostic for easier reporting.

New auto-heal system:
* NEW: scripts/ensure_ready.py — checks every expected AI model and
  downloads any that are missing / truncated.
* NEW: ENSURE-READY.bat — friend-facing wrapper. Double-click any
  time the demo seems broken or after setting HF_TOKEN for real STT.
* UPDATED: SETUP-FRIEND.bat now calls the auto-heal as its final
  step — setup only declares COMPLETE if every model is usable.
* UPDATED: README-FOR-FRIEND.md explains the flow.

Net effect: the demo is guaranteed to boot. If a model is missing
and can be downloaded, it is. If a gated model can't be obtained,
the service falls back to a mock engine with a clear message telling
you how to get the real one later.


How to apply the update
-----------------------

1. Close any running demo (close the four AaaS service terminal
   windows if they're open).

2. Unzip THIS zip into the SAME parent folder as AaaS-Portable.
   Example: if your install is C:\AaaS\AaaS-Portable\, unzip this
   into C:\AaaS\. Let Windows overwrite existing files.

3. Double-click ENSURE-READY.bat (this is NEW in this update). It
   will verify every AI model and auto-download anything missing.
   First run takes seconds if all models are intact; longer if
   something needs downloading.

4. Reload the browser extension:
   * Open chrome://extensions in Chrome/Edge
   * Find "AaaS Accessibility Companion (Odisha)"
   * Click the circular reload icon

5. Refresh any demo page tabs.

6. Done. Run RUN-DEMO.bat to boot the services.


If something feels wrong
------------------------

Widget: open DevTools (F12) on a demo page, Console tab, hover an
element, look for [AaaS/hover] — that log line tells us what text
the widget extracted and what it's about to speak.

Models: double-click ENSURE-READY.bat. It prints a line per model:
  [OK]   — model present and healthy
  [MISS] — couldn't find it; will attempt download
  [HEAL] — downloaded successfully just now
  [FALLBACK] — gated model unavailable, mock engine configured
  [FAIL] — couldn't heal; action required (internet / HF access)

Setup failures: scroll up in the SETUP-FRIEND.bat window for the
first red [X] line.
