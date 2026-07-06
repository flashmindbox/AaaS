# AaaS — Pitch Playbook

**Team:** SUBARNAREKHA
**Project:** Accessibility as a Service — built for Odisha, designed for every
Indian public institution.
**One-liner:** *One button on any government website that reads, translates,
simplifies, scans and listens — in Odia, by voice. Odisha first, India next.*

Pick the variant that fits the slot you get. Each one is written to be spoken,
not read. Practise aloud until you hit the time. Every claim below is
demoable on the laptop — nothing here is roadmap dressed as product.

---

## The 15-second hook (judge walks up to the booth)

> "Every Odisha government site is English-first and screen-reader-broken, and
> the important notices are scans — photographs of paper. We built one button
> that reads any page aloud in Odia, translates it, reads the scanned
> circulars, and fills forms by voice. It's running — want to see the scanned
> one? That's the fun part."

Then go straight to the Read-document demo. Don't pitch past the hook.

---

## The 60-second pitch (elevator / intro round)

**Problem.** Odisha has over 21 lakh persons with disabilities and 42 million
Odia speakers. Nearly every public portal — pensions, scholarships, results,
grievances — is built English-first, keyboard-only, and screen-reader-broken.
Worse: the documents that matter most are *scans*. To a blind citizen, a
scanned circular does not exist.

**Solution.** AaaS is one floating button any website gets with a single
script tag — or our browser extension puts it on sites that haven't adopted
it yet. Six things, all working today: it **reads pages aloud in Odia** with a
follow-along highlight; **translates whole pages** to Odia in place;
**simplifies** bureaucratic language; **reads scanned notices and PDFs** —
OCR, then Odia, side by side with the original; **fills forms by voice**,
asking for each field aloud and writing names in English letters without
mangling them; and **navigates by voice command**, even to links hidden in
menus and carousels.

**How.** Four small AI services on-prem — AI4Bharat's IndicWav2Vec and
IndicTrans2, Meta's MMS-TTS, Tesseract OCR — behind one gateway. No cloud, no
per-user data, DPDP-friendly, runs on one laptop today and OCAC's data centre
tomorrow. Apache-2.0.

**Ask.** One pilot: one district portal, one board site. The integration is a
script tag. Then watch the rest of the state follow.

---

## The 3-minute pitch (booth / panel round)

**Open — the human.** *[Look up, make eye contact before starting.]*
Picture Arun. He's sixty-eight, a farmer near Jajpur, arthritis in both hands,
and he speaks only Odia. His village water pipe broke three weeks ago. The
grievance portal exists — it's in English, it wants typed input, and the
notification about repair schedules is a scanned photograph of a paper
notice. Arun's government is online; Arun is not. His grandson files the
complaint. Twenty-one lakh Odias with disabilities live some version of this
story every week.

**What we built.** One button — ଅ — that sits on any website. For Arun it does
six things, and I can show you all six right now on this laptop:

1. **Reads any page aloud in Odia**, highlighting each line as it speaks, with
   skip and replay — like a patient relative reading the news.
2. **Translates the whole page to Odia** in place, and un-translates with one
   tap.
3. **Easy Read** rewrites officialese into plain language — offline,
   rule-based, no hallucinations, because a wrong deadline in a government
   notice is worse than no notice.
4. **Reads scanned documents.** It finds the scan or PDF, runs OCR locally,
   translates it, and shows the original page and the Odia text side by side
   while reading aloud — the citizen sees the stamp and the reference number
   *and* understands them.
5. **Fills forms by voice.** It walks field by field, asks for each answer
   aloud in Odia, beeps, listens. His name lands as "Purnnachandra" — not
   "full moon", which is what naive translation does to Odia names. Spoken
   numbers become digits. And it never presses Submit — the citizen always
   does.
6. **Navigates by voice.** Say "ଟେଣ୍ଡର" and it opens Tenders — even though
   the speech model heard an English word through Odia ears, and even though
   the link was hidden inside a carousel. When it's not sure, it shows
   buttons instead of guessing. No dead ends.

**Why it's infrastructure, not an overlay.** Accessibility overlays are
rightly criticised for ticking boxes without helping anyone. We are the
opposite: we don't claim the page is now WCAG-compliant — we give the citizen
a working alternative path through it. One deployment at OCAC serves every
department that adds the script tag; our browser extension covers every site
that hasn't yet. It's the UPI pattern: shared rails, one integration,
everyone benefits. Apache-2.0, so Odisha exports a standard instead of buying
a product.

**The Bhashini answer, pre-empted.** Bhashini is the engine layer — voices as
APIs. We're the product on top: engines don't do guided form-filling, name
transliteration, or side-by-side scanned-notice reading. We'd plug Bhashini in
tomorrow as a backend. Bhashini gives India voices; AaaS gives Odisha's
citizens hands, eyes and ears.

**Close.** Everything I described ran live, on this laptop, on mirrors of
real Odisha government sites — and through our extension on the *actual*
Jajpur district portal. One script tag per site. One pilot is all we're
asking for. Odisha first, India next.

---

## Taglines (pick per audience)

- For judges: **"Bhashini gives India voices. AaaS gives Odisha's disabled
  citizens hands, eyes and ears."**
- For officials: **"Your portals stay exactly as they are. Your citizens stop
  needing help to use them."**
- For technologists: **"Four on-prem models, one gateway, 520 KB of widget,
  zero cloud calls."**
- For everyone: **"Odisha first, India next."**

## Forbidden claims (this section survives every rewrite)

- No models we don't ship: never say Whisper, IndicConformer, Piper, or LLM.
  We ship IndicWav2Vec, IndicTrans2, MMS-TTS, Tesseract, and our rule engine.
- No exam module, no avatar-as-feature (three.js concept = roadmap exhibit).
- No invented latency or WER numbers — demo instead of quoting.
- No "WCAG-compliant" claims about host pages — we add an assistive path; we
  don't certify their markup.
