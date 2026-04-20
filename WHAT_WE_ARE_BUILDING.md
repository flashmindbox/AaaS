# What We Are Building — In Plain English

**Project:** Accessibility as a Service (AaaS) for Public Institutions
**Team:** SUBARNAREKHA
**Document created:** 2026-04-20
**Companion to:** `PLAN.md` (the technical blueprint)

This document explains — without jargon — what we are building, who it is for,
and what it feels like to use. If the technical plan is the *recipe*, this is
the *meal on the plate*.

---

## 1. The Problem We Are Solving

We are building this for Odisha first. Imagine three real people in the
state today:

- **Priyanka**, a visually impaired college student from Puri who speaks
  only Odia, tries to download her exam hall ticket from Utkal University's
  portal. The page is in English. It has no screen reader support. The
  "Download" button is an image with no label. She asks her younger
  brother to do it for her every time.

- **Arun**, a block-office clerk near Sambalpur nearing retirement, has a
  mild learning difficulty and struggles with the dense Odia text on the
  new e-district portal. He prints everything and fills it by hand, then
  has someone else key it in.

- **Meera**, a Class 10 student with dyslexia at a school in Cuttack, is
  about to take a board-affiliated online mock test. The Odia text is small,
  crammed, and the font makes conjuncts hard to distinguish. There is no
  option to have questions read aloud. She gives up halfway.

Today, every institution in Odisha that wants to solve these problems has
to build its own solution — hire developers, buy screen-reader licences,
record Odia voices, test with disabled users. It is expensive,
inconsistent, and almost never happens well. So the people above keep
getting left out.

Our platform fixes this **once, centrally, in Odia first**, and lets any
institution in the state (and eventually the country) plug it in — the way
they plug in payments or SMS today.

---

## 2. The Big Idea in One Paragraph

We are building a single, shared, on-prem-capable service — deployable at
OCAC in Bhubaneswar — that gives any public institution in Odisha (and
eventually in the rest of India) the accessibility features their users
need. Institutions do not build Odia speech, reading, translation, or
exam-accommodation tools themselves. They simply "turn on" ours. A
student, a citizen, or an officer using any of these institutions gets
the same high-quality Odia-first experience — read-aloud in their
language, simplified text, high-contrast views, sign language support,
accessible exams — across every portal they visit.

Think of it as **"electricity for accessibility"**: every institution in
the state plugs into the same grid. The grid starts in Odisha and grows
outward.

---

## 3. Who Uses It

Four kinds of people will interact with the platform, each differently.

### 3.1 End users (the citizens and students we ultimately serve)

- **Visually impaired users** — blind or low-vision; need screen readers,
  audio, high contrast, Braille output where available.
- **Hearing impaired users** — deaf or hard-of-hearing; need captions,
  sign language, visual alerts.
- **Users with learning differences** — dyslexia, ADHD, cognitive
  differences; need simpler language, dyslexia-friendly fonts, chunked
  reading, more time.
- **Motor-impaired users** — limited hand movement; need full keyboard
  navigation, voice control, large targets.
- **Speakers of Indian languages other than English** — over 80% of
  Indians; need everything in their mother tongue, not just English. In
  our first-pilot state of Odisha, this means **Odia first** — 42 million
  Odia speakers whose primary interface to government must be in their
  own language, in their own script.
- **Elderly citizens** — often a combination of the above; need everything
  bigger, simpler, slower, and spoken.

They never "log in" to our platform. They experience it as a small
accessibility button on their institution's website, or a voice at a
kiosk, or better settings inside their exam.

### 3.2 Institution staff (our direct customers)

- University registrars, exam controllers, e-governance officers,
  school headteachers, portal webmasters.
- They sign up their institution, get an API key, paste a single line
  of code into their website, and configure what they want enabled.

### 3.3 Government and regulators

- Ministry of Social Justice, MeitY, DEPwD, UGC, state IT departments.
- They get compliance dashboards, audit reports, adoption numbers.

### 3.4 Our own operators

- Platform admins, accessibility testers (including testers who are
  themselves disabled), content moderators, support engineers.

---

## 4. What It Feels Like — User Stories

This is the clearest way to describe what we are building. Each story
shows one feature from the user's point of view.

### Story A — Priyanka downloads her hall ticket

Priyanka visits the Utkal University portal on her phone. She presses
`Alt + A`. A small, focused panel slides in. She says in Odia,
*"ପୃଷ୍ଠାଟି ପଢ଼ନ୍ତୁ"* ("Read the page"). A clear Odia voice — one of
AI4Bharat's Indic-TTS voices — reads the page in order, skipping the
decorative banners and jumping to the important links. When she reaches
the "Download Hall Ticket" button — which the portal forgot to label —
our engine has already looked at it, decided it says "Download Hall
Ticket," translated it to Odia, and announces that. She downloads her
ticket herself. It took 40 seconds.

**What we built for this:** the web accessibility widget, the Odia
text-to-speech engine, the Odia speech-to-text engine, and the
auto-labelling of unlabelled elements using image and layout
understanding.

### Story B — Arun applies for a scheme at the block office

Arun walks up to a kiosk at the Sambalpur block office. A friendly
screen greets him in Odia, large and high-contrast, using the formal
ଆପଣ. He taps the "ମୋ ସହିତ କଥା କୁହନ୍ତୁ" ("Talk to me") button and says,
"ମୁଁ କନ୍ୟା ଯୋଜନା ପାଇଁ ଆବେଦନ କରିବାକୁ ଚାହୁଁଛି" — "I want to apply for the
Kanya Yojana scheme." The kiosk walks him through every field by voice,
confirms each answer back to him in Odia, and lets him correct any
mistake. It prints a simplified receipt he can read. He never touched a
keyboard.

**What we built for this:** the kiosk hardware profile, Odia
speech-to-text, voice-driven form filling, and text simplification.

### Story C — Meera takes her mock exam in Odia

Meera opens the exam link for a BSE Odisha mock test. The portal detects
she is registered as a student with dyslexia and automatically configures
the exam: Noto Sans Oriya with wider line spacing and increased
word-spacing (letter-spacing breaks Odia conjuncts — our design system
knows this), a "read this question aloud in Odia" button next to every
question, and 25% extra time per the RPwD Act. She answers the MCQs by
clicking; for the one-line short answers she dictates in Odia and
confirms the transcription in Odia script. She finishes the paper. Her
certificate, when it arrives, is a proper accessible PDF she can read
with her screen reader.

**What we built for this:** the accessible exam engine, candidate
accommodation profiles, Odia-specific dyslexia reading mode, Odia
speech-to-text answer capture, and tagged (accessible) PDF generation.

### Story D — A deaf citizen watches an Odisha Government video

An Odisha Health & Family Welfare Department video on seasonal flu
vaccination plays. Below the video, captions appear in real time in
Odia. In the corner, a small 3D sign-language avatar signs the key
phrases in Indian Sign Language. A Deaf citizen in Bhubaneswar
understands the announcement without needing a family member to
interpret.

**What we built for this:** real-time Odia captioning, Odia-to-English
translation for cross-state reuse, and the ISL avatar phrase-book.

### Story E — An OCAC engineer onboards a district portal

Rajesh, an engineer at OCAC working on the Ganjam district portal,
hears about our service through his IT Secretary's 5T review. He visits
our site, signs the district up for the free tier under the state's
umbrella agreement, gets an API key, and pastes one line of code into
the district portal's header. He goes to our admin dashboard, picks
Odia and English, turns on read-aloud and high-contrast, and turns off
the exam module (he does not need it). The accessibility widget is live
on his portal in 15 minutes. He then runs our audit tool, which tells
him four images on the home page have no alt text. He fixes them that
afternoon — and submits the dashboard screenshot as evidence to the
monthly 5T review.

**What we built for this:** the admin dashboard, the one-line JS SDK,
tenant configuration, and the accessibility audit tool.

---

## 5. The Features, One by One, in Plain Words

### 5.1 Read-Aloud (Text-to-Speech)

Any page, any content, read out in a clear human-sounding voice. **Odia
is our reference language** — we use AI4Bharat's Indic-TTS which has two
production-quality Odia voices (male and female). For English we use
Piper. For Hindi and other Indic languages, whichever model gives
better quality for that language. The user can speed up, slow down,
pause, resume. For people who cannot see the screen, or prefer to
listen, or are driving, or can read some languages but hear others
better.

### 5.2 Dictation (Speech-to-Text)

Speak, and your words become text. Works on forms, search boxes, exam
answers. **For Odia we use AI4Bharat's IndicConformer**, which
outperforms Whisper on Odia by 10+ points of word-error rate. Mixed
Odia-English speech ("Odia-English code-mix") is common in urban
Odisha; we route those to a fallback Whisper-large model. Phase 2
adds Sambalpuri and Kosali dialect robustness.

### 5.3 Translation

Any content from one Indian language to another, instantly. A
government circular written in English can be read in Bengali. A Tamil
notice can be understood by a Marathi speaker. The translation respects
important terms — "Aadhaar", "PAN", "District Magistrate" — and leaves
them untouched using a shared institutional glossary.

### 5.4 Screen Reader Overlay

For websites that never implemented proper accessibility, our overlay
injects the missing labels, navigation shortcuts, and structure so that
screen readers (theirs or ours) can actually work. It is not a magic
fix, but it closes most common gaps without the institution having to
rewrite their site.

### 5.5 Dyslexia & Learning Mode

Changes how text appears. For Latin text, a font designed for dyslexic
readers (OpenDyslexic) with wider letter spacing. **For Odia, we cannot
use OpenDyslexic — it doesn't support the script, and positive
letter-spacing actually breaks Odia conjuncts.** So our Odia dyslexia
mode takes a different approach: keep Noto Sans Oriya, push line-height
to 1.9 (from the already-generous 1.7 we use for Odia by default), add
word-spacing, and auto-switch to a high-contrast theme. A highlighter
moves with the reading. "Bionic reading" bolds the first half of each
word. Complex sentences can be simplified while preserving meaning —
the simplifier is Odia-native, not a translate-and-paraphrase
roundtrip.

### 5.6 High-Contrast and Visual Modes

One-click switches for high-contrast, dark mode, large text, and
motion-reduced view. Respects what the user has already set in their
operating system.

### 5.7 Keyboard and Voice Navigation

Everything on the page reachable without a mouse. Shortcuts that do
not collide with the host site. Voice commands like "go to main menu"
or "next question".

### 5.8 Image Description

If a picture on the page has no alt text, our engine generates a short
description for it — "a chart showing rising enrolment from 2020 to
2025" — so a blind user is not left in silence.

### 5.9 Indian Sign Language (ISL) Support

For deaf users who do not read written Indian languages fluently,
a 3D signing avatar plays key phrases in ISL. Starts as a curated
phrase-book (forms, instructions, announcements) and grows.

### 5.10 Accessible Examinations

An exam system that understands disability. Candidates register their
accommodation needs once; every exam after that is automatically set up
for them — extra time, audio questions, dictated answers, dyslexia
mode, scribe support — without them having to ask every time.

### 5.11 Accessibility Audit

An institution pastes their URL into our tool and gets a report: what
is wrong, how bad, how to fix it, and an estimated effort. This helps
institutions fix their websites at the source, not just rely on our
overlay.

### 5.12 Admin Dashboard

For the institution staff: sign up, get API keys, choose what to turn
on, see how many people used each feature, download compliance reports
for their regulator.

### 5.13 Mobile App — SaralAccess

A free app for citizens. Point it at any printed document (a form, a
notice, a bill) and it reads it aloud. Point it at any object and it
describes what it sees. Fill government forms by voice. Works even
when offline, with slightly smaller models.

### 5.14 Physical Kiosks

Touch-and-voice kiosks for district offices, bus stations, post
offices. Affordable tablet-class hardware running our software, with
microphone, speaker, and optional Braille display. Works with an NFC
card for citizens who want to save their preferences.

### 5.15 Developer SDKs

For institutions that build their own apps and websites: ready-to-use
libraries for JavaScript, React Native, Android, and iOS that handle
all of the above with a few lines of code.

---

## 6. How an Institution Plugs In

This is the onboarding path, end to end.

1. An institution signs up on our portal, verifies itself (government
   institution ID or a letter from its authority).
2. It creates a "tenant" — a private workspace for its data, users,
   and settings.
3. It gets an API key and chooses a plan (public institutions below
   a size threshold are free).
4. For a website: paste one line of JavaScript into the page.
   For a mobile app: add our SDK.
   For a kiosk: flash our image on an approved Android tablet.
5. In the admin dashboard, it turns on the features it needs — languages,
   read-aloud, dyslexia mode, exam accommodations — and sets its branding.
6. It runs our audit on its own site, gets a report, and optionally
   assigns us the remediation work.
7. Its users experience accessibility the next time they open the site.

There is **no long integration project, no custom contract, no six-month
procurement cycle** to get to basic accessibility. That is the whole point.

---

## 7. What Keeps It Safe, Private, and Trustworthy

Accessibility tools touch sensitive data — voices, faces, disability
records, exam papers. We take that seriously.

- **Consent first.** Nothing is recorded by default. Microphone access is
  explicit, per session, and visible.
- **Data stays in India.** All servers and model inference run inside
  Indian data centres, as required by the DPDP Act 2023.
- **Minimum data.** We do not store audio or text beyond what is needed
  to answer the current request, unless the user opts in to help
  improve our models.
- **No advertising, no profiling.** The platform never serves ads and
  never sells data.
- **End-user control.** A citizen can export or delete everything the
  platform knows about them, at any time, from a single page.
- **Transparent models.** We publish how accurate our speech and
  translation are for each Indian language. If a language has
  60% accuracy we say so — we do not pretend otherwise.
- **Security certifications.** We work toward ISO 27001, CERT-In empanelment,
  and STQC certification before any large-scale government rollout.
- **Human oversight.** Decisions that affect an exam result, an
  accommodation approval, or any significant outcome are reviewable
  by a human — never fully automated in silence.

---

## 8. The Rollout Story — What Gets Built, When, and Why

This is the same roadmap as the technical plan, but described by
**what users can actually do after each phase**.

### Phase 0 — Foundations (first 2 weeks)

Nothing user-visible. We set up the workshop: code repository, quality
checks, development environment, security model. After this, the team
can build fast without cutting corners on accessibility or security.

### Phase 1 — Minimum Usable Platform (weeks 3-8)

After this phase, an Odisha pilot institution (Utkal / IIT Bhubaneswar /
NIT Rourkela) can put our widget on its website and its users get:

- **Read-aloud in Odia**, English, and Hindi — Odia the default for
  Odisha tenants
- Large text, high contrast, dyslexia mode tuned for Odia
- Keyboard-only navigation
- **Dictation in Odia** for search boxes and form fields

The institution staff can self-serve from a simple dashboard (in Odia).
We prove the core architecture works with Odisha as the live pilot.

### Phase 2 — Languages and Stronger Assistance (weeks 9-14)

After this phase:

- Odia is production-quality and battle-tested; 11 more Indian
  languages come online (Hindi, Tamil, Telugu, Bengali, Marathi,
  Gujarati, Kannada, Malayalam, Punjabi, Urdu, Assamese)
- Sambalpuri / Kosali / Desia dialect benchmark for Odia is published
- A screen-reader overlay for sites that lack basic accessibility
- Dyslexia and learning-difference reading mode — Odia-specific rules
  included — with plain-language simplification
- Early Indian Sign Language support through a phrase-book avatar
- An accessibility audit tool any institution can run on itself

This is the phase where the platform becomes genuinely useful to
non-English speakers and to learners beyond Odisha as well.

### Phase 3 — Accessible Examinations (weeks 15-20)

After this phase:

- Students with disabilities can take real online exams with automatic,
  pre-configured accommodations
- Examiners can administer accessible tests without any special
  technical knowledge
- Certificates come out as properly accessible PDFs
- The whole exam path is usable end-to-end by a visually impaired,
  hearing impaired, dyslexic, or motor-impaired candidate

This is the highest-impact single use case in India and why exam boards
will be among our first paying customers.

### Phase 4 — Mobile and Kiosks (weeks 21-26)

After this phase:

- Citizens can use our mobile app to read any document, describe any
  picture, and fill forms by voice
- Kiosks can be installed in district offices, post offices, and
  railway stations for citizens who do not own smartphones
- Everything works even with poor or no internet

This is the phase where we reach the people who are hardest to reach —
rural citizens, elderly citizens, and citizens without smartphones.

### Phase 5 — National Scale and Compliance (weeks 27-40)

After this phase:

- The platform is certified for large-scale government use
- It integrates with DigiLocker, NAD, UDISE+, NIC eOffice, and major
  exam formats
- Institutions across multiple states can onboard through a standard
  playbook
- A public dashboard shows how many institutions are using what, and
  how well each language performs

This is the phase where the platform becomes a public good, not a
product.

### Phase 6 — Ongoing Research and Expansion

After this, we keep growing: more tribal languages, better sign
language translation, a plugin marketplace, a community of disabled
testers and contributors. The platform gets better every quarter
from the data and the feedback it gathers.

---

## 9. Why This Will Work

- **The technology already exists.** Open-source speech, translation,
  and reading tools from AI4Bharat (IndicConformer, Indic-TTS,
  IndicTrans2), OpenAI Whisper, and others are already strong enough for
  production use in Indian languages. We are integrating, not inventing.
- **The demand is enormous and unmet.** India has more than 26 million
  people with disabilities (2011 Census; real number much higher). **In
  Odisha alone, over 21 lakh persons with disabilities and 42 million
  Odia speakers are served poorly or not at all by digital government.**
- **It is cheaper to share than to duplicate.** One Odisha university
  building a speech system costs more than the ~200 BPUT-affiliated
  colleges using a shared one.
- **It is aligned with policy.** The state's 5T and Mo Sarkar
  programmes, the Odisha IT Policy 2022, India's Digital India and
  Accessible India initiatives, the Rights of Persons with Disabilities
  Act 2016, and the DPDP Act 2023 all push in this direction. The policy
  environment rewards this work.
- **It is the right thing to do.** Every citizen has a right to use
  their own government's services in their own language. Accessibility
  is not a feature; it is a part of citizenship.

---

## 10. What Success Looks Like

One year from launch, if this succeeds:

- 50+ public institutions in Odisha have onboarded — targeting Utkal,
  IIT Bhubaneswar, NIT Rourkela, OUAT, all BPUT affiliates, and OCAC's
  shared-services portals.
- Odia is in production at full quality; 11 more Indian languages are
  live on the same platform.
- BSE Odisha or a state exam board has conducted an accessible exam in
  Odia using our platform.
- 500,000+ end users — disabled, elderly, non-English/Odia-only
  speakers in Odisha — have used one of our features in the past month.
- Odisha Government has made our platform part of its default
  e-governance stack, likely under the 5T umbrella.
- 5T accessibility metrics are showing measurable improvement month
  over month.

Three years from launch, it has grown from Odisha outward — the default
accessibility layer of public digital India — invisible to most,
life-changing for the millions who need it.

---

## 11. What We Are **Not** Building

To keep scope honest:

- **We are not** a replacement for good website design. Institutions
  should still fix their sites. Our audit tool exists to help them.
- **We are not** a proctoring or surveillance system. Our exam engine
  favours dignity over invasive monitoring.
- **We are not** a content platform — we do not publish government
  content, we make existing content accessible.
- **We are not** a closed commercial silo. We prefer open models,
  open standards, and portable data.

---

## 12. The One-Line Summary

> **A single, trustworthy, Odia-first accessibility layer — built for
> Odisha, designed for every Indian public institution — that any
> government body can switch on in a day, so that no citizen is shut
> out of their own state.**

That is what we are building. Odisha first. India next.
