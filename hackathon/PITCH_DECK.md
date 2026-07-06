# AaaS Pitch Deck — Slide-by-Slide Build Spec

This document rebuilds `pitch/AaaS-Pitch.pptx` around the shipped product.
Every slide gives you: **ON SLIDE** (the exact words — keep them, slides are
not documents), **VISUAL** (what to draw or screenshot, with URLs), and
**SAY** (speaker notes). 12 slides, 7 minutes with the live demo at slide 5.

---

## Design system (set once in the master)

| Element | Value |
|---|---|
| Canvas | White `#FFFFFF`, footer strip navy `#0D2444` |
| Primary | Navy `#14335D` (headings, diagrams) |
| Accent | Saffron `#F0821E` (one highlight per slide, never more) |
| Success | Green `#157A3C` · Alert red `#B3261E` |
| Category colours | blue `#1A5CC8` · maroon `#8A2432` · green `#157A3C` · saffron `#E07B12` · teal `#0E7D70` · violet `#6236C9` |
| Font | Segoe UI (Semibold for titles) — already on every Windows machine |
| Odia font | Noto Sans Oriya (install on the presenting laptop; it's in the repo) |
| The mark | The ଅ glyph, white on a navy rounded square — top-right of every slide |
| Footer | `AaaS · Team SUBARNAREKHA · Smart Odisha Hackathon '25` |

Screenshot rule: every screenshot below comes from the running stack
(`start-dev.bat`, then the URL given). Capture at 1920×1080, browser zoom
100%, F11 full-screen so no browser chrome shows.

---

## Slide 1 — Title

**ON SLIDE**
> ଅ  (large, centred, the navy tile — 1/3 of the slide)
> **AaaS — Accessibility as a Service**
> One button that reads, translates, simplifies, scans and listens —
> in Odia, by voice.
> Team SUBARNAREKHA · Smart Odisha Hackathon '25

**VISUAL** — The ଅ mark huge and centred; the seven feature chips from the
demo gallery in a row beneath the tagline (screenshot the chip row from
`http://127.0.0.1:8000/demo/` or redraw as rounded rectangles in the six
category colours).

**SAY** — "Good morning. Everything you'll see in the next seven minutes is
running live on this laptop — no cloud, no mock-ups. I'll show you a citizen
using it, then how it works."

---

## Slide 2 — The problem (Arun)

**ON SLIDE**
> Arun, 68. Farmer near Jajpur. Arthritis. Speaks only Odia.
> His water pipe broke three weeks ago.
> - The grievance portal is **in English**
> - It wants **typed input**
> - The repair notice is a **photograph of paper**
>
> **His government is online. Arun is not.**

**VISUAL** — Left half: the pension-notice scan image
(`apps/demo-sites/ssepd-odisha/assets/pension-notice-scan.png`) tilted
slightly, like paper. Right half: the four bullet lines. The last line alone,
saffron, larger.

**SAY** — "This is not an edge case. Odisha has twenty-one lakh persons with
disabilities by the 2011 census — undercounted — and forty-two million Odia
speakers. The most important documents their government publishes are scans:
to a blind citizen, this notice does not exist."

---

## Slide 3 — Why this stays broken

**ON SLIDE**
> Every portal fixes accessibility alone — badly, or not at all.
> - 100s of government websites, each its own project
> - Overlay widgets tick boxes; they don't help anyone
> - Screen readers can't read a scan, and read English at Odia speakers
>
> Accessibility must be **infrastructure, not remediation.**

**VISUAL** — A grid of ~12 grey website favicons/rectangles each with a
red ✗; one saffron arrow sweeping under them toward slide 4. Keep it stark.

**SAY** — "The failure pattern is structural: every department buys its own
fix. The insight of UPI and DigiLocker is that shared rails beat a hundred
private projects. Nobody has built those rails for accessibility. We did."

---

## Slide 4 — The solution: one button

**ON SLIDE**
> **ଅ** — one button on any government website
> 🔊 Read aloud (follow-along highlight) · 🌐 Translate → Odia (undo)
> 📖 Easy Read plain language · 📄 Scanned documents, side by side
> 🎙️ Fill forms by voice · 🧭 Navigate by voice
> 🅾 OpenDyslexic comfort · ruler · hover-to-speak
>
> Integration = **one script tag**. Sites not integrated? **Our browser
> extension injects it anyway.**

**VISUAL** — Screenshot of the widget panel open on the SSEPD site
(`http://127.0.0.1:8000/demo/ssepd-odisha/`, click ଅ): the six-tile icon
grid with Odia labels. Place it right; bullets left. This is the product's
face — give it room.

**SAY** — "Six capabilities behind six tiles, labelled Odia-first because the
user is Odia-first. And two integration paths: one script tag for the
government, or our extension for any site the citizen visits today."

---

## Slide 5 — LIVE DEMO (switch to browser)

**ON SLIDE** (shown only if the projector needs a placeholder)
> Live: ssepd-odisha demo · ~4 minutes
> 1. Read aloud + highlight → 2. Translate + Easy Read (↺)
> 3. Scanned circular, side by side, spoken in Odia
> 4. Pension form filled entirely by voice
> 5. "ଟେଣ୍ଡର" — voice command on the real Jajpur site

**INSTRUCTION** — Follow `hackathon/DEMO_SCRIPT.md` scenes 1–5. Pre-warm the
caches before judges arrive (the script's setup section). If the mic dies,
the script's fallback section switches to the recorded run — do NOT debug on
stage.

**SAY** — the demo script's lines. The one sentence to land before switching
back: "Everything you just saw ran on this laptop, offline."

---

## Slide 6 — How it works

**ON SLIDE**
> citizen's browser → **gateway :8000** (auth · audit · proxy)
> → TTS :8001 Meta MMS · STT :8002 IndicWav2Vec · Translate :8003
> IndicTrans2 + rule-based simplify + Tesseract OCR
> X-API-Key per tenant · every engine has an honest mock fallback

**VISUAL** — Do NOT redraw this. Screenshot the "How a request flows"
diagram from the operator console (`http://127.0.0.1:8000/admin/`, bottom
section) — browser card → saffron arrows → gateway → rail → three service
cards. It's already in deck style.

**SAY** — "Four small services behind one gateway. The models are the best
open Indic AI available — AI4Bharat's IndicWav2Vec and IndicTrans2, Meta's
MMS voices, Tesseract for scans. On-prem: at OCAC's data centre in
production, on this laptop today. DPDP-friendly by construction — voice is
processed in memory and discarded."

---

## Slide 7 — The hard parts (what WE built)

**ON SLIDE**
> The models are commodities. The product is what's between the citizen
> and the model.
> - MMS-TTS is **mute on digits** → we speak "୩୦୦ ଟଙ୍କା" as Odia words
> - Odia STT hears English **phonetically** → "କଣ୍ଟାକ୍ଟ" finds *Contact*
> - Translation turns the name Purnnachandra into **"full moon"** → we
>   transliterate names, never translate them
> - Sites hide their notices in **carousels** → our voice nav reaches them

**VISUAL** — Four rows, each: red "before" fragment → saffron arrow → green
"after" fragment (e.g. `ପୂର୍ଣ୍ଣଚନ୍ଦ୍ର → "full moon" ✗` → `Purnnachandra ✓`).
Monospace for the fragments.

**SAY** — "If a judge remembers one slide, make it this one. Each line is a
real failure we hit this month and fixed — they're why a wrapper around the
same models would not work in front of a real citizen."

---

## Slide 8 — It's real: six tenants, live numbers

**ON SLIDE**
> One gateway, six kinds of institution:
> district · university · exam board · welfare dept · hospital · central govt
> **228 automated checks · offline USB bundle · real OCR inside**

**VISUAL** — Two screenshots side by side:
1. The demo gallery card grid (`http://127.0.0.1:8000/demo/`) — six colours.
2. The operator console KPI row + tenants table (`http://127.0.0.1:8000/admin/`)
   — take it AFTER some demo use so the counters are non-trivial.

**SAY** — "Six demo tenants, from a district collectorate to AIIMS to the
National Scholarship Portal — because the same rails serve all of them. The
console on the right is live: every number is the gateway's own audit log,
and judges are welcome to press the buttons — there's an API playground and
a two-step onboarding flow that mints a working key."

---

## Slide 9 — "Doesn't Bhashini do this?"

**ON SLIDE**
> Bhashini = the language **engine** layer (ASR · MT · TTS as APIs)
> AaaS = the accessibility **product** on top
>
> Engines don't do guided form-filling, name transliteration,
> never-auto-submit safety, or side-by-side scanned reading.
> **We'd plug Bhashini in tomorrow — it makes us stronger.**
>
> *Bhashini gives India voices. AaaS gives Odisha's disabled citizens
> hands, eyes and ears.*

**VISUAL** — Two-layer diagram: wide navy base bar "Language engines
(Bhashini · AI4Bharat · Meta)" with a saffron layer on top "AaaS —
accessibility product", and citizen icons standing on the saffron layer.

**SAY** — Deliver the tagline slowly. If pressed with "so you're just a UI":
"So is UPI — the rails existed; the product made a billion people use them.
The last mile is the product. Ours is the ଅ button."

---

## Slide 10 — Adoption: the UPI pattern

**ON SLIDE**
> The state deploys once. Every department adds **one script tag.**
> ```html
> <script src="https://aaas.ocac.gov.in/widget.js"
>         data-key="aaas_live_…" defer></script>
> ```
> Apache-2.0 · no vendor lock-in · any SI can operate it
> Other states adopt free → **Odisha exports the standard**

**VISUAL** — Centre: one navy gateway node. Radiating: 8–10 small portal
cards in the category colours. The script tag in a code box, saffron border.

**SAY** — "This is the whole integration — we demoed the console minting a
key and this exact snippet. The economics: one deployment at OCAC, every
portal onboards itself. Apache-2.0 means Odisha doesn't buy a product; it
sets a standard the rest of India can copy."

---

## Slide 11 — Honest limits & roadmap

**ON SLIDE**
> Honest today:
> - OCR: printed notices yes, handwriting no
> - STT wants clear speech — so we retry, and show tappable choices
> - USB bundle ships mock translation (torch doesn't fit); laptop runs real
>
> Next:
> - Pilot: one district portal + one board site
> - Native-speaker polish of the Odia glossary
> - Bhashini as an alternate engine backend
> - More languages: engines already support them — it's configuration

**VISUAL** — Two columns, "Today" (grey chips) and "Next" (saffron chips).
No diagram; let the honesty read as confidence.

**SAY** — "We'd rather tell you the limits than have you find them. None of
them are architectural — the roadmap is pilots and polish, not rewrites."

---

## Slide 12 — Close

**ON SLIDE**
> ଅ
> **Odisha first. India next.**
> One pilot is all we ask.
> Team SUBARNAREKHA · [contact / QR to repo]

**VISUAL** — Near-empty slide: the mark, the tagline, a QR code (generate to
the repo or a demo video). Navy on white.

**SAY** — "Arun shouldn't need his grandson to talk to his own government.
One script tag fixes that — we've shown it working on six kinds of
institution, offline, in Odia. Odisha first, India next. Thank you."

---

## Assembly checklist

1. Run `start-dev.bat`, pre-warm (DEMO_SCRIPT setup), take the five
   screenshots listed above at F11 full-screen.
2. Build the master slide: white canvas, navy footer strip, ଅ mark top-right,
   Segoe UI, install Noto Sans Oriya for the Odia strings.
3. Paste ON-SLIDE text verbatim — resist adding sentences; the SAY column is
   for your mouth, not the slide.
4. Slide 5 stays a placeholder — the demo happens in the browser. Alt-Tab,
   don't embed video unless it's the fallback recording.
5. Export a PDF copy alongside the PPTX (projector-proof), and put both in
   `pitch/` next to the old deck (keep the old one as `-v1`).
6. Rehearse against the timing budget in DEMO_SCRIPT.md: slides 1–4 ≈ 2 min,
   demo ≈ 4 min, slides 6–12 ≈ 3 min if questions run long, cut 10 and 11 —
   never 7 or 9.
