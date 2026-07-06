# AaaS — Judge Q&A Prep

Every answer below is written to be spoken in 15–45 seconds. If you start to
ramble, stop. Judges prefer a crisp "I don't know — we plan to find out" over
a two-minute improvisation.

Questions are grouped by what the judge is really probing for. Under pressure,
identify the *type* of question first, then pull the answer.

---

## Category 0 — "Why Odisha? Why Odia?"

These are the most common opening questions at an Odisha hackathon. Nail these
and the rest of the conversation goes easier.

### Q. Why Odisha first? Hindi has more speakers.

**A.** Three reasons. One — Odisha has an *active digital-service mandate* the
state is held publicly accountable to: 5T and Mo Sarkar are real programmes
with real political weight behind them. Two — Odia is *under-served* by global
tooling: Whisper has no usable Odia at all; we run AI4Bharat's IndicWav2Vec,
trained on Indic speech specifically. That gap is the work most projects skip.
Three — the team is from Odisha. Infrastructure adoption is relationship-driven;
we start where we can credibly land a pilot.

### Q. How does this fit with 5T and Mo Sarkar?

**A.** 5T's pillars — Transparency, Technology, Teamwork, Time-limit,
Transformation — all apply to a citizen being able to *actually use* a
government service. Mo Sarkar asks citizens whether they got what they came
for; for an Odia-speaking disabled citizen on a state portal today, the honest
answer is "no". One script tag makes the answer "yes" — without rebuilding the
portal.

### Q. How would an Odisha institution actually adopt this?

**A.** Three paths in parallel. Bottom-up: a single IT cell at a university or
board adds the script tag to its own site — that's a one-line change. Through
OCAC: the state IT agency operates many citizen portals on shared
infrastructure, so one deployment touches many services. Top-down: the 5T cell
positions it as state policy. Our demo mirrors Jajpur's district portal and
BSE Odisha because those are exactly the sites a pilot would start with.

---

## Category 1 — Technology ("do they actually understand their stack?")

### Q. Which AI models are you running?

**A.** Four engines, all running on this laptop: AI4Bharat's **IndicWav2Vec**
for Odia speech-to-text, AI4Bharat's **IndicTrans2** — the distilled 200M,
CPU-friendly — for translation, Meta's **MMS-TTS** for Odia, Hindi and English
voices, and **Tesseract** for OCR on scanned notices. Easy Read simplification
is our own rule engine — deterministic, fully offline.

*Never say: Whisper, IndicConformer, Piper, NLLB, or any LLM. We don't run
them. (NLLB exists as a config option; it is not shipped.)*

### Q. Why not Whisper?

**A.** Whisper has no usable Odia. IndicWav2Vec is trained for Indic speech.
Our extension's optional on-device mode does use a small Whisper for
Hindi/English offline — Odia always routes to IndicWav2Vec.

### Q. Why rules for simplification instead of an LLM?

**A.** Because a government notice with a hallucinated deadline is worse than
no notice. Rules are deterministic, auditable line by line, run offline on a
₹30,000 laptop, and never invent facts. An LLM can slot in behind the same API
later — the widget wouldn't change.

### Q. This looks like a wrapper around existing models. What did YOU build?

**A.** The models are commodities; the product is everything between the
citizen and the model. Four examples: MMS-TTS is **silent on digits** — we
verbalize numbers into Odia words, so "୩୦୦ ଟଙ୍କା" is actually spoken. The Odia
STT writes English words **phonetically in Odia script** — we sound-match
"କଣ୍ଟାକ୍ଟ" to the real "Contact" link. Naive translation turns the name
Purnnachandra into **"full moon"** — we transliterate names instead. And
government sites hide their most-wanted links inside carousels — our voice
navigation reaches them anyway. None of that ships in any model.

### Q. What happens when a model fails, or there's no internet?

**A.** Every engine has a deterministic mock fallback and the widget's status
pill says which engine answered — the demo degrades honestly instead of dying.
Nothing needs the internet except translating third-party pages when the local
engine is down.

### Q. What does a website need to change to adopt this?

**A.** One script tag. The widget is ~520 KB of self-contained JavaScript —
no dependencies, no build step, Shadow-DOM isolated so it can't break the host
page's styling and the host page can't break ours. For sites we don't control,
the browser extension injects the identical widget — that's how we ran it on
the live jajpur.odisha.gov.in.

---

## Category 2 — Architecture, security, privacy

### Q. How does this scale beyond one laptop?

**A.** Four stateless FastAPI services behind a gateway with per-tenant API
keys — scaling is standard container operations. Caching does the heavy
lifting: repeated synthesis and translations are served from cache (browser
IndexedDB plus server-side LRU), so the expensive path runs once per sentence,
not once per user. In production this lives at OCAC's data centre.

### Q. What about DPDP / data privacy?

**A.** Voice never leaves the deployment. No accounts, no PII stored — audio
is processed in memory and discarded; the widget keeps only preferences,
locally in the browser. On-prem at OCAC keeps data residency in-state. We do
not log content — usage counters per feature only.

*Don't claim: Keycloak, Postgres row-level security, MinIO, mTLS. That was an
earlier architecture sketch; the shipped system is deliberately simpler —
API-key tenancy at the gateway with a seed registry. Say "the tenant registry
is a seed file today; swapping in a database is configuration, not redesign."*

### Q. Latency?

**A.** Show, don't quote: first synthesis of a sentence takes a few seconds on
CPU; everything repeated is cached and instant — that's why the demo pre-warms.
OCR of a two-page circular runs in seconds. If they want numbers, run it in
front of them; never quote figures from memory.

---

## Category 3 — Scope honesty ("what are they hiding?")

### Q. Sign language support?

**A.** Roadmap, honestly labelled. We built a three.js proof-of-concept and
made the call that a half-good avatar would hurt deaf users more than help.
We chose to perfect voice, reading and forms first. The concept demo is in the
repo at /demo/avatar-preview/.

### Q. Wasn't there an exam module?

**A.** We cut it — deliberately, for focus. The widget serves every government
page *including* exam portals, which covers the underlying need without us
maintaining a parallel exam product.

### Q. Which languages, and what does adding one cost?

**A.** Odia, Hindi, English live today. The engines underneath support most
scheduled languages, so a new language is configuration plus native-speaker
testing, not new architecture. Odia-first was the point — it's the
hardest-served major language, and it's ours.

### Q. What breaks if I try it on a random website right now?

**A.** Please try it — that's what the extension is for. We tested six real
sites this week — jajpur.odisha.gov.in, bseodisha.ac.in, odisha.gov.in,
ssepd.odisha.gov.in, iitbbs.ac.in, india.gov.in — and fixed what we found:
duplicate links freezing the matcher, font-size buttons matching everything,
notices hidden in carousels. Honest limits today: voice matching shows you
candidate buttons when it isn't confident, and OCR wants printed text, not
handwriting.

### Q. Odia OCR quality?

**A.** Printed government notices: good. Poor scans: modest — we use
tessdata_fast for speed on CPU. The side-by-side view is partly an honesty
feature: the citizen always sees the original next to our reading of it.

---

## Category 4 — Impact and sustainability

### Q. Who pays for this?

**A.** The state, once, for all departments — that's the "as a Service" model.
One deployment at OCAC serves every portal that adds the script tag.
Apache-2.0: no vendor lock-in, any SI can operate it, other states adopt it
free — Odisha exports the standard instead of buying a product.

### Q. How do you measure impact?

**A.** Feature-level usage counters per tenant at the gateway — which pages
get read aloud, which forms get voice-filled — with zero content logging. That
tells a district collector which services citizens struggle with. That's
policy signal, not just accessibility metrics.

### Q. What's next after the hackathon?

**A.** Three concrete steps: a pilot with one district portal and one board
site; a native-speaker pass on the Odia glossary and panel wording; and
Bhashini integration as an alternate engine backend. None of them change the
architecture.

---

## Category 5 — The Bhashini question (it WILL come)

### Q. Doesn't Bhashini already do this?

**A.** Bhashini is the language-engine layer — ASR, translation, TTS as APIs.
AaaS is the **accessibility product on top of** that layer. Bhashini gives
India voices; AaaS gives a blind Odia citizen a way to *fill a grievance form
by speaking*, *hear a scanned circular in Odia*, *navigate a website without
dead ends*. Engines don't do guided form filling, name transliteration,
never-auto-submit safety, or side-by-side scanned-document reading — products
do. We would plug Bhashini in as a backend tomorrow; it makes us stronger, not
redundant.

**Follow-up: "So you're just a UI?"**
> So is UPI — the rails existed; the product made a billion people use them.
> The last mile is the product. Ours is the ଅ button.
