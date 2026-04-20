# AaaS — Pitch Playbook

**Team:** SUBARNAREKHA
**Project:** Accessibility as a Service — Built for Odisha, designed for every Indian public institution.
**One-liner:** *The UPI of accessibility — an open, shared, Odia-first layer any public institution can plug into.*

Pick the variant that fits the slot you get. Each one is written to be spoken, not read. Practise aloud until you hit the time.

---

## The 15-second hook (judge walks up to the booth)

> "Every public-university website in Odisha fails accessibility. We built an open-source layer — design system, Odia-first voice AI, and a compliance scorecard — that any institution can deploy in an afternoon. Think UPI, but for accessibility. Odisha first, India next."

Pause. Let them ask the next question. Don't pitch past the hook.

---

## The 60-second pitch (elevator / intro round)

**Problem.** Odisha has over 21 lakh persons with disabilities and 42 million Odia speakers. Yet nearly every public-institution portal in the state — admissions, scholarships, pensions, exams — is built English-first, keyboard-hostile, and screen-reader-broken. Each of Odisha's 15+ state universities and 200+ BPUT-affiliated colleges tries to fix it alone, badly or not at all.

**Insight.** Accessibility shouldn't be 200 separate projects. It should be shared digital public infrastructure — the way UPI is for payments and DigiLocker is for documents. And for Odisha's citizens, it should start in Odia.

**Solution.** AaaS is three things in one open-source stack:
1. A **design system** where every component ships WCAG 2.2 AA out of the box — AAA colour contrast, 44 px touch targets, keyboard-first, screen-reader-clean, with Noto Sans Oriya and Odia-aware typography bundled in.
2. An **assistive services layer** — on-prem Odia voice (AI4Bharat IndicConformer + Indic-TTS), translation (IndicTrans2), captions, dyslexia-friendly reading mode tuned for Odia script — that users toggle on demand.
3. A **compliance scorecard** any institution can run on their own site and watch trend upward over time.

**Status.** Foundations are live today — design system, accessibility test harness, dev stack, threat model, DPDP data-flow, Odia language strategy document. Apache-2.0. On-prem-capable, so data never leaves Odisha.

**Ask.** We want the minimum viable *public* accessibility layer. Adopt it for one Odisha institution. Fork it. Fund it. Then watch the rest of the state follow.

---

## The 3-minute pitch (booth / panel round)

**Open — the human.** *[Look up, make eye contact before starting.]*
Picture Priyanka. She's blind, she's in Class 12 in Puri, she speaks only Odia, and next week she has to fill an online admission form for Utkal University. Today, that form defeats her — the labels aren't linked to inputs, the captcha is image-only, the page is in English, the error messages flash red and disappear. She asks her brother to fill it for her. Half of Odisha's disabled students end up doing the same.

**The scale.** Odisha has over 21 lakh persons with disabilities by the conservative 2011 Census — the real number is higher. It has 15+ state universities, 200+ BPUT-affiliated colleges, 62,000+ schools, and a unified citizen-services stack run by OCAC. Every one of them legally owes accessibility under the Rights of Persons with Disabilities Act and the state's own 5T mandate — and almost none of them deliver it.

**Why this keeps failing.** Because we've been treating accessibility as a per-project checkbox. Each institution hires a vendor, bolts on an "overlay" widget, ticks the box, moves on. Overlays are widely criticised by the disability community for not actually fixing anything. And no one measures the outcome.

**Our thesis.** Accessibility has to become *infrastructure*, not *remediation*. Three pieces:

1. **`@aaas/ui`** — a React design system. Priyanka's admission form, built with our `Button` and `Input` and `Form` components, is accessible at commit time — not after a QA cycle. Contrast is AAA by default. Every focus state is visible. Noto Sans Oriya is bundled, line-height is tuned for Odia conjuncts, dyslexia mode flips one attribute.

2. **`@aaas/a11y-test`** — a harness that any institution runs against their own deployment. Machine-readable report per WCAG 2.2 criterion. Shows up in CI on every pull request.

3. **The assistive widget** — a small floating button. Priyanka taps it, speaks in Odia, and her voice drives the form. AI4Bharat IndicConformer for Odia speech, IndicTrans2 for translation into English for downstream processing, AI4Bharat Indic-TTS for the Odia voice back. All on-prem. All open weights. DPDP-compliant because data never leaves the institution's VM — the institution's VM being, in this case, OCAC's data centre in Bhubaneswar.

**Demo tease.** *[Gesture to laptop.]* I'll show you Priyanka, Arun — who's dyslexic — and Meera, who's Deaf, all three Odia speakers, using the same portal in three very different ways. 90 seconds.

**Close.** We're calling the project SUBARNAREKHA — after the river that flows through Jharkhand and Bengal and empties into the Bay of Bengal at Odisha's Balasore coast. Subarna means gold; Rekha means streak. The river carries gold downstream to everyone on its banks. That's the intent. Accessibility shouldn't belong to whoever hires the best vendor. It should belong to every Odia speaker, and then to every Indian.

---

## The 5-minute pitch (main stage / final round)

Use the 3-minute pitch, and after "DPDP-compliant because data never leaves the institution's VM", insert:

**The technical bet.** We chose three non-obvious things.

*One — we're not a widget-only play.* Widgets treat broken HTML as a given and patch around it. That's why the a11y community calls them snake oil. We ship the design system *and* the assistive services, so institutions who use our components never need remediation, and institutions who can't rewrite yet still get something useful.

*Two — we're on-prem first.* Every other accessibility SaaS is a cloud tenant with your users' speech and reading patterns on someone else's servers. Under DPDP, for a public institution that's a liability. Our reference deployment runs Whisper, Piper, and IndicTrans2 on a single GPU node inside the institution's own data centre.

*Three — Odia is not an afterthought, and neither are the other Indian languages that follow.* Most global accessibility tooling treats Hindi as a translation target and everything else as "other". We're treating **Odia as the primary reference language**, and 11 other Indian languages as first-class input on the same rails. The voice models are fine-tuned on IndicCorp. The fonts ship with Noto Sans Oriya, Devanagari, Tamil, Bengali. The dyslexia stack has Odia-specific conjunct-safe rules — you cannot just set `letter-spacing: 0.12em` on Odia text, it breaks conjuncts. We do the work global tooling skips.

**What we've shipped so far.** *[Name only what is actually built at demo time — honesty builds trust with judges who've heard too much vaporware.]*

**What's next.** Phase 1 is multi-tenant auth and the API gateway. Phase 2 is the embed widget. Phase 3 is the Indic AI services. We have a realistic path to all of it — we've already stood up the dev stack, and the threat model, DPDP flow, and WCAG acceptance checklist are written and tracked in the repo.

**The ask.** Three things, in order of how much you can help: (1) pilot this at one Odisha institution you have influence in — Utkal, IIT Bhubaneswar, NIT Rourkela, OUAT, or an OCAC-run portal; (2) connect us to the Odisha IT Dept or the 5T cell in the Chief Minister's Office; (3) contribute upstream. Apache-2.0, repo link on the booth card.

**Close.** The cost of building accessibility once, well, and sharing it, is less than the cost of 600 institutions each failing at it separately. That's our one-line case. Thank you.

---

## Taglines (pick one, stay consistent all weekend)

- **The UPI of accessibility — Odisha first, India next.** *(use with govt / 5T / infrastructure-minded audience)*
- **Accessibility, not an afterthought. Odia, not a translation target.** *(use with designers, language activists, academics)*
- **One public layer. Two hundred campuses in Odisha. Forty-two million Odia speakers.** *(use with scale-minded funders)*
- **Built into the component, not bolted onto the page.** *(use when distinguishing from overlays)*
- **ଓଡ଼ିଶା ପାଇଁ, ଓଡ଼ିଶା ଠାରୁ।** (*Odisha paiñ, Odisha tharun.* — "For Odisha, from Odisha." — use to open Odia-speaking audiences.)

---

## Phrases to use

- "Digital public infrastructure" — not "SaaS platform"
- "Odia-first, Indian-public-institution-first" — not just "multilingual"
- "Assistive services layer" or "augmentation widget" — never "overlay" (it's a slur in the a11y community)
- "Aligned with 5T and Mo Sarkar" — any time you're talking to Odisha govt audience
- "On-prem at OCAC's data centre" — more concrete than "on-prem" alone
- "Open source, Apache-2.0" — say it early, it changes the room

## Phrases to avoid

- "AI-powered" as a standalone claim — always name the model
- "Solves accessibility" — we enable it, we don't solve it
- "Disabled people" in generic voice — use "people with disabilities" or specific communities (blind, Deaf, dyslexic)
- "Fixes bad websites" — we replace bad patterns, not paper over them

---

## Numbers to know cold

**Odisha-specific**

- **42 million+** Odia speakers (L1 + L2 worldwide; ~37.5M L1 per 2011 Census)
- **21 lakh+** persons with disabilities in Odisha (2011 Census — undercounted)
- **4.65 crore** Odisha population
- **15+** state universities, **200+** BPUT-affiliated colleges, **62,000+** schools
- **6th classical language** of India — Odia, declared 2014
- **5T + Mo Sarkar** are the state's digital-service mandates we align with

**India-wide context**

- **60 million+** Indians with disabilities (conservative — WHO's 16% estimate puts it higher)
- **22** scheduled languages in the Constitution; we target **12** in Phase 3, **Odia first**

**Platform**

- **WCAG 2.2 AA** is our compliance floor; **AAA** for colour contrast specifically
- **44 px** minimum touch target (WCAG 2.5.8)
- **≥1.7** line-height for Odia text (vs 1.5 for Latin)
- **Apache-2.0** license
- **Zero** user data leaves the tenant's infrastructure in our reference deployment
