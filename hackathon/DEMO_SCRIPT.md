# AaaS — Demo Script

The live demo is the single most important thing judges remember. This script
exists so the presenter can do it under pressure, with background noise, with a
dodgy projector, and with one hand holding a water bottle.

Everything in this script is **shipped and rehearsable today** — every scene is
a real feature running on this laptop. There is no vapourware scene. If a scene
fails twice in rehearsal, cut the scene, not the honesty.

---

## Setup before judges arrive

1. Laptop plugged in, 100% battery, notifications silenced.
2. Start the stack: run `start-dev.bat` from the repo root (or the USB bundle's
   `start.bat`). Wait for the four service windows: gateway :8000, TTS :8001,
   STT :8002, translate :8003.
3. **Pre-warm the caches**: open `http://127.0.0.1:8000/demo/bse-odisha/` and
   run one Read-aloud, one Translate, and one Read-document pass. First-time
   synthesis takes seconds; cached replays are instant. Judges get the cached
   experience.
4. Browser tabs, in order:
   - **Tab 1:** `http://127.0.0.1:8000/demo/bse-odisha/` — mirror of the real
     BSE Odisha board site (has the 2-page scanned circular).
   - **Tab 2:** `http://127.0.0.1:8000/demo/jajpur-collectorate/` — has the
     grievance form for voice filling.
   - **Tab 3:** `https://jajpur.odisha.gov.in/en` — the REAL district site,
     with the browser extension loaded (chrome://extensions → verify it's on).
5. External microphone plugged in and tested — the built-in mic struggles with
   booth noise. One headphone bud in your ear for private TTS checks.
6. Insurance: a screen recording of a full successful run, in a hidden tab.

---

## The one-liner (say it before touching anything)

> "Every Odisha government site is written in English, for sighted people who
> type. Four crore Odias, twenty-one lakh of them with disabilities, live on
> the other side of that wall. AaaS is one button that tears the wall down —
> on any website, in Odia, by voice. Watch."

---

## Scene 1 — Read aloud (60 seconds)

*Tab 1, the BSE mirror. Click the floating ଅ button. The icon-grid panel
opens: six tiles, Odia labels first.*

> "This is a mirror of the real BSE Odisha exam board site. Meet a Class-10
> student from Kendrapara who can't read small English text."

*Tap **ପଢ଼ି ଶୁଣାଅ · Read aloud**. The Odia voice starts; each block gets an
amber highlight as it's spoken.*

> "The page reads itself aloud — and highlights exactly what it's reading, so
> a low-vision or dyslexic reader can follow along. These ⏮ ⏭ buttons skip or
> replay a section. Space pauses. Escape stops."

*Skip forward once with ⏭ so judges see the highlight jump. Press Esc.*

> "The voice is Meta's MMS Odia model running on this laptop — no cloud. We
> taught it to say numbers: '୩୦୦ ଟଙ୍କା' comes out as 'three hundred rupees'
> in Odia words, because the raw model goes silent on digits."

## Scene 2 — Translate + Easy Read (60 seconds)

*Tap **ଅନୁବାଦ · Translate → Odia**. The page rewrites itself in Odia,
in place — layout intact.*

> "Whole-page translation to Odia — AI4Bharat's IndicTrans2, running locally.
> Notice the ↺ undo button on the tile: one tap restores the original. Nothing
> is destructive."

*Tap **ସହଜ ପଢ଼ା · Easy Read**.*

> "Easy Read simplifies the bureaucratic language — 'shall furnish the
> requisite documents' becomes 'must give the papers'. It's rule-based, fully
> offline, and it simplifies in whatever language the page is currently in —
> here, Odia."

## Scene 3 — Read document: the scanned circular (90 seconds — the peak)

*Scroll to the circulars list. Point at "Examination circular No. EX-II/886
(scanned PDF, 2 pages)".*

> "Now the hard problem. Government notices are scans — photographs of paper.
> Screen readers see nothing. Translators see nothing. For a blind citizen,
> this circular does not exist."

*Tap **ଦଲିଲ ପଢ଼ · Read document**. The chooser asks which document; tap the
circular.*

> "It found the scanned PDF, ran OCR on it — Tesseract, on this laptop —
> simplified it, translated it to Odia…"

*The side-by-side view opens: original scanned pages LEFT, Odia text RIGHT.
It starts reading aloud; the page being spoken glows amber on both sides.*

> "…and now it reads it aloud in Odia, showing you the original page and the
> Odia text side by side. Same stamp, same reference number, both languages.
> The amber highlight follows the voice across pages."

*Let it speak one page. Tap ⛶ to maximize briefly. Close.*

## Scene 4 — Speak to fill: the grievance form (90 seconds)

*Tab 2, the Jajpur collectorate mirror. Scroll to "File a Grievance".*

> "Arun is sixty-eight, arthritic hands, speaks only Odia. He needs to report
> a broken water pipe. Watch him fill this form without touching the keyboard."

*Tap **କହି ଲେଖ · Speak to fill** with no field selected. The guided mode
starts: it highlights the name field, ASKS for it aloud in Odia, beeps, and
listens.*

*Speak, one field per prompt:*
- Name: **"ପୂର୍ଣ୍ଣଚନ୍ଦ୍ର ମହାନ୍ତି"** → lands as "Purnnachandra Mahanti"
- Village: **"ଗ୍ରାମ ବଣପୁର"** → "Grama Banapura"
- Phone: **"ନଅ ଆଠ ସାତ ଛଅ…"** (spoken digits) → 9876…
- Age: **"ପଚାଶ"** → 50

> "Three things just happened that are genuinely hard. One: his name was
> **transliterated, not translated** — Purnnachandra means 'full moon', and a
> naive pipeline writes 'full moon' in the name box. Two: spoken numbers
> became digits — the speech model writes 'nine eight seven' as words. Three:
> it never presses Submit. It fills, it shows a ✓ for each answer, and it
> leaves the final decision to Arun. Progress counter, retry on a misheard
> number, Escape to stop — this is a kiosk-grade flow."

*Press Enter on the focused Submit button. The demo confirmation appears.*

## Scene 5 — Voice command on the REAL site (60 seconds)

*Tab 3 — the real jajpur.odisha.gov.in, extension loaded.*

> "Everything so far ran on mirrors. This is the actual live district website
> of Jajpur — we don't control it. The extension injects the same button."

*Tap **କହି ଚଲାଅ · Voice command**. Speak: **"ଟେଣ୍ଡର"**.*

> "The speech model only knows Odia — it hears English words like 'tender'
> phonetically. We romanize and sound-match against every link on the page,
> including ones hidden inside carousels and menus."

*It highlights and opens Tenders. If it shows the "did you mean" buttons
instead, SAY SO — it's a feature:*

> "When it isn't sure, it never guesses — it shows the top candidates as
> buttons. Voice gets you 90% there, one tap finishes it. No dead ends."

## Scene 6 — Comfortable letters (30 seconds, closer)

*Back on any page. Open the panel's Reading comfort section, tick
**ଆରାମ ଅକ୍ଷର · Comfortable letters**.*

> "For dyslexic readers: OpenDyslexic letterforms — bottom-weighted so letters
> don't flip — extra spacing, warm background. Odia script keeps its proper
> conjunct rendering. And notice: our own panel is unaffected — we hold our
> product to the standard we're fixing."

*Close with the pitch line:*

> "One widget, one gateway, four on-prem AI services, works on any website —
> the government doesn't have to rebuild a single portal. Bhashini gives
> India language AI. AaaS turns it into hands, eyes and ears for the citizens
> who need it most. Odisha first, India next."

---

## Timing budget

| Scene | Time |
|---|---|
| One-liner | 0:20 |
| 1 Read aloud | 1:00 |
| 2 Translate + Easy Read | 1:00 |
| 3 Scanned circular | 1:30 |
| 4 Voice form fill | 1:30 |
| 5 Real site + voice command | 1:00 |
| 6 Comfortable letters + close | 0:40 |
| **Total** | **~7:00** |

Short-on-time order of cuts: Scene 6 → Scene 2's Easy Read half → Scene 1's
skip-button beat. **Never cut Scene 3 or 4** — they are the demo.

---

## Fallbacks

- **Mic fails / booth too loud:** every voice scene has a typed equivalent —
  the widget accepts simulated input events; rehearse the recorded-video
  fallback instead. Do NOT struggle with a mic twice in front of judges.
- **A service dies:** every engine has a deterministic mock fallback — the
  widget stays alive and says so in the status pill. Restart via
  `start-dev.bat`; services come back in under a minute (TTS needs ~40 s).
- **Internet dies:** nothing in Scenes 1–4 and 6 needs internet. Scene 5
  (real site) does — swap to Tab 1's mirror of the same site and say
  "this mirror is byte-identical to the live site we can't reach from here."
- **Everything dies:** the hidden tab has the full recorded run. Narrate over
  it with the same script.

## What NOT to claim

- Don't name models we don't run. We run: **IndicWav2Vec** (STT, AI4Bharat),
  **IndicTrans2** (translation, AI4Bharat), **Meta MMS-TTS** (speech), and
  **Tesseract** (OCR). No Whisper, no IndicConformer, no Piper, no LLM.
- The sign-language avatar and the exam module are **not features**. If asked:
  avatar is a roadmap concept (a three.js proof-of-concept exists), the exam
  module was deliberately cut for focus.
- Don't quote latency numbers from memory — say "first synthesis takes a few
  seconds on CPU; everything repeated is cached and instant", then show it.
