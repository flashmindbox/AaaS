# Presenter One-Pager — Know This Cold

Carry this in your pocket. Read it five times on the train to the venue. You
should be able to answer every line from memory.

---

## Identity

- **Team name:** SUBARNAREKHA — the river that flows from Jharkhand through
  Bengal and empties into the Bay of Bengal at Odisha's Balasore coast.
  Subarna = gold, Rekha = streak. The river carries gold to Odisha. We're
  infrastructure built *for* Odisha, flowing *from* open-source.
- **Project name:** AaaS — Accessibility as a Service — built for Odisha,
  designed for every Indian public institution.
- **One-liner:** *One button on any government website that reads, translates,
  simplifies, scans and listens — in Odia, by voice. Odisha first, India next.*
- **Team:** Pratikshya Padhi (Class XI), the only member · Odisha Adarsha
  Vidyalaya, Jamdhar · Guide teacher: Somali Priyadarshini Mohanty
  (98611 37602) · Odiapreneur 3.0, theme *Accessibility, Ecommerce &
  Cyber Security*.
- **License:** Apache-2.0. Say this early in any conversation.

---

## What it is (30-second version)

One floating ଅ button that works on **any** website — via a one-line embed or
our browser extension — backed by four small services running **on-prem**
(this laptop today; OCAC's data centre in production):

1. **The widget** — six features behind six tiles: Read aloud (with follow-along
   highlight), Translate → Odia, Easy Read simplification, Read document (OCR
   for scanned notices/PDFs with side-by-side view), Speak to fill (guided
   voice form filling), Voice command navigation. Plus OpenDyslexic
   "Comfortable letters", a reading ruler, and hover/selection speech.
2. **The AI services** — Odia STT (AI4Bharat IndicWav2Vec), translation
   (AI4Bharat IndicTrans2), speech (Meta MMS-TTS, or/hi/en), OCR (Tesseract),
   and a fully offline rule-based text simplifier — behind one gateway with
   API-key tenancy.

Nothing leaves the machine. Every feature has a deterministic mock fallback,
so the demo cannot die.

---

## What is BUILT vs planned (get this right)

**Built, working, demoable now:**
- All six widget tiles + comfort toggles, verified on real government sites
  (jajpur.odisha.gov.in, bseodisha.ac.in, odisha.gov.in, ssepd.odisha.gov.in)
- Browser extension (MV3, v0.4.0) — injects the widget into any site
- Four services + gateway, 240+ automated checks green
- Odia number-speech in TTS (digits → spoken Odia words)
- Name **transliteration** (not translation) for voice form fill
- Spoken-number understanding (Odia words, phonetic English, "double" forms)
- Portable package (`SUBARNAREKHA-Setup.zip`): the full real stack runs
  offline on any Windows laptop, nothing to install

**Roadmap (say "designed for, not built"):**
- More Indic languages beyond or/hi/en (the engines already support them)
- Sign-language avatar — a three.js concept demo exists, deliberately deferred
- WCAG audit tooling for site owners

**Cut (say "we cut it for focus" if asked):**
- The accessible mock-exam module — removed, not deferred.

---

## Numbers to memorise

**Odisha (say these first to any Odisha-audience judge)**

| What | Number |
|---|---|
| Odia speakers worldwide | ~42M (L1: ~37.5M per 2011 Census) |
| Odisha population | ~4.2 crore (2011 Census) |
| Odisha literacy | 72.9% — about 27% aged 7+ cannot read (2011 Census) |
| Persons with disabilities, all India | 2.68 crore = 2.21% (2011 Census) |
| Odia — declared classical language | 2014 (6th in India) |
| State IT agency | OCAC |
| State digital mandate | 5T + Mo Sarkar |

**Platform**

| What | Number |
|---|---|
| Widget size, self-contained | ~520 KB, zero dependencies |
| Services | 4 (gateway, TTS, STT, translate+OCR+simplify) |
| Automated checks | 240+ across 5 suites |
| Languages live today | Odia, Hindi, English |
| Real sites verified | 6 incl. jajpur.odisha.gov.in, india.gov.in |
| Cloud calls required | 0 (fully on-prem) |

---

## The stack (never misname these)

| Job | Model / engine | Who made it |
|---|---|---|
| Speech → text (Odia) | **IndicWav2Vec** | AI4Bharat |
| Translation | **IndicTrans2** (distilled 200M) | AI4Bharat |
| Text → speech (or/hi/en) | **MMS-TTS** | Meta |
| OCR (scans, PDFs) | **Tesseract** | open source |
| Simplification (Easy Read) | rule-based, ours | us — fully offline |

NOT in the stack: Whisper, IndicConformer, Piper, NLLB (available as an
option, not shipped), any LLM, any cloud API. If a judge asks "why not an
LLM?" — "Rules are deterministic, auditable, run offline on a ₹30,000 laptop,
and can't hallucinate a wrong deadline into a government notice."

---

## Differentiation (the three answers that win)

1. **"Doesn't Bhashini do this?"** — Bhashini is the language engine layer;
   we're the accessibility product ON TOP of engines like it. Bhashini gives
   India voices; AaaS gives Odisha's disabled citizens hands, eyes and ears —
   guided form filling, scanned-notice reading, never-dead-end voice nav.
   We'd plug Bhashini in as a backend tomorrow.
2. **"Why not just use Chrome's built-in reader?"** — Chrome doesn't speak
   Odia numbers, doesn't OCR scanned circulars into side-by-side Odia,
   doesn't fill forms by voice, and doesn't transliterate names. We do those
   four things *because* we're built Odia-first, not translated-in.
3. **"What's hard about this?"** — The demo hides the hard parts: MMS-TTS is
   mute on digits (we verbalize numbers in Odia), STT writes English words
   phonetically in Odia script (we sound-match them to real links), naive
   translation turns the name Purnnachandra into "full moon" (we
   transliterate), and government sites hide their most important links in
   carousels (we reach them anyway).

---

## Honest weaknesses (own them before judges find them)

- Odia OCR quality on poor-quality scans is modest (tessdata_fast) — printed
  notices yes, handwriting no.
- STT needs reasonably clear speech; booth noise hurts — that's why the
  guided form fill retries and the voice nav shows "did you mean" buttons.
- Translating a long page for the first time takes a couple of minutes on
  CPU; after that it is cached and instant.
- One-student team, hackathon timeline — breadth over per-feature depth,
  by design.
