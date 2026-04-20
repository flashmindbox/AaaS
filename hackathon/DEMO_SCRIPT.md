# AaaS — Demo Script

The live demo is the single most important thing judges remember. This script exists so the presenter can do it under pressure, with background noise, with a dodgy projector, and with one hand holding a water bottle.

Two tracks are documented. Pick one on the morning of the demo based on what is actually shipped and stable at that point. Never attempt the Full-Vision track if Phase 3 AI services are flaky — a broken demo kills the pitch. The Foundation track is honest, short, and wins on substance.

---

## Track choice (decide the morning of the event)

| Track | Requires | Length | When to pick |
|---|---|---|---|
| **Full-Vision** | Phase 0 + widget + at least one working Indic AI service | 5–7 min | Everything above is stable across 3 consecutive rehearsals |
| **Foundation** | Phase 0 only | 3–4 min | Any AI service has failed in rehearsal today |

If in doubt, pick Foundation. A clean, honest demo of real infrastructure beats a broken demo of promised AI every time.

---

# Track A — Full-Vision Demo (5–7 minutes)

## Setup before judges arrive

1. Laptop plugged in, 100% battery, airplane mode off, all notifications silenced.
2. Two browser windows side by side:
   - **Left:** `https://utkal-university.aaas.local/admissions` — the seeded Odisha demo tenant, Odia default locale.
   - **Right:** `https://utkal-university.aaas.local/admin` — the compliance dashboard, already logged in.
3. A third tab, hidden, pointing at a **recorded screen capture of a successful run**. This is your insurance policy. See the Fallback section.
4. External microphone plugged in and tested. The on-laptop mic struggles with booth noise.
5. One headphone bud in your own ear — a judge may want to listen to the TTS output privately.
6. Water, throat spray, business card / QR code holder on the table.

## Scene 1 — The baseline (30 seconds)

*Open on the admissions form, scrolled to the top. Page is in English, as most Odisha state-uni sites are.*

> "This is Utkal University's admissions portal — realistic, it looks like most Odisha state-university sites today. English-first, dense, keyboard-hostile. Let's see what accessibility looks like for three Odia-speaking students trying to use it."

Scroll down the form once. Don't over-explain. Let the density of the form speak for itself.

## Scene 2 — Priyanka, blind applicant, Odia speaker (90 seconds)

*Click the floating AaaS button, bottom-right. Page switches to Odia-labelled variant — Noto Sans Oriya renders crisply.*

> "Priyanka is blind. She's from Puri. She speaks only Odia. She taps this button and talks to the form."

*Hold the mic up, speak naturally in Odia:*
> "ନମସ୍କାର, ମୁଁ ବି.କମ୍ ପାଇଁ ଆବେଦନ କରିବାକୁ ଚାହୁଁଛି।"
> *(Transliterated: Namaskar, mun B.Com pain abedan kariba-ku chahunchhi.)*
> *(Translation: "Hello, I want to apply for B.Com.")*

*Pause — let the on-screen transcription appear in Odia script. Let the Odia voice reply play.*

Narrate over the response:
> "Behind this, three models are running on-prem. AI4Bharat's IndicConformer for her Odia speech — roughly 15% word-error rate, much better than Whisper for Odia. IndicTrans2 if we need to bridge to English for downstream processing. AI4Bharat's Indic-TTS for the Odia voice back. Zero user data leaves this laptop. In production, it lives at OCAC's data centre in Bhubaneswar — compliant with DPDP and the state's data-residency mandate."

*Ask one more question, then let Priyanka dictate one form field. Her Odia dictation appears in Odia script.*

Close the scene:
> "She filled in her name by voice. In Odia. On a form that, without us, she could not see at all, let alone fill in her language."

## Scene 3 — Arun, dyslexic applicant reading Odia (45 seconds)

*Open the widget, switch to the "Reading" tab, flip "Dyslexia mode" on.*

Narrate as the page visibly transforms:
> "Arun is dyslexic. He reads Odia. One toggle. The page has re-rendered — but watch closely, because Odia is not Latin. We can't just swap to OpenDyslexic — it doesn't support Odia script. What we do instead: keep Noto Sans Oriya, bump line-height to 1.9, increase word-spacing not letter-spacing — letter-spacing breaks Odia conjuncts — and switch to our high-contrast theme. Every rule here is Odia-specific, documented in our language-strategy doc."

*Scroll to a long policy paragraph, tap "Summarise in Odia".*

> "Long Odia text becomes three Odia bullets. That's a local LLM summarising into the same language, not translating away. Runs on the same on-prem GPU."

## Scene 4 — Meera, Deaf applicant (30 seconds)

*Navigate to the "Welcome from the Vice-Chancellor" video page — the VC is speaking Odia.*

*Play the video with live captions on.*

> "Meera is Deaf, from Cuttack. The VC is speaking Odia. Captions are generated on the fly in Odia script, with proper punctuation and conjunct rendering. Phase 2 adds an Indian Sign Language avatar overlay — we're already in touch with ISLRTC Delhi about corpus access."

Mute the video after 5 seconds. Don't let it eat your time.

## Scene 5 — The admin reveal (60 seconds)

*Switch to the right-hand window — the admin dashboard.*

> "Now flip to the Utkal registrar's view. Every Odisha institution using AaaS gets this."

Point at the numbers:
> "WCAG 2.2 compliance score for this site today — [read the number]. We ran 47 automated checks. Three failures on the admissions form, all mapped to a specific WCAG criterion. Fix buttons suggest the exact code patch."

Point at the usage counters:
> "And live today: 147 Odia voice sessions, 23 dyslexia-mode, 61 captions. The registrar sees exactly which assistive features Odisha students are actually using. This is the kind of measurement 5T and Mo Sarkar can report to the CM's office without a consultant."

## Scene 6 — The integration reveal (45 seconds)

*Open a terminal or a code pane showing a tiny snippet.*

> "Here's what an Odisha institution does to adopt this. Three lines in their HTML, and their tenant key. That's it. Same infrastructure serves every tenant. Tenants are isolated — no data crosses institutions, no data leaves the state. Fully on-prem-capable — runs on a single VM at OCAC. Apache-2.0 license. QR code on the table for the repo."

## Scene 7 — Close (15 seconds)

Stand up straight, eye contact:
> "Twenty-one lakh persons with disabilities in Odisha. Forty-two million Odia speakers. Two hundred colleges. Today, each one is inaccessible alone. We're making accessibility a shared public utility — infrastructure, not a product. Odisha first. India next. Happy to go deep on any of it."

Stop talking. Wait for questions.

---

# Track B — Foundation Demo (3–4 minutes)

Use this if any AI service is flaky or the widget is not yet integrated. Lean into what is real.

## Scene 1 — The harness (90 seconds)

Open a terminal. Run:

```bash
pnpm --filter @aaas/a11y-test exec aaas-a11y audit https://some-real-state-university.ac.in
```

*Let the output scroll. Point at the failures as they print.*

> "This is what every public-institution website looks like today under WCAG 2.2. Labels missing, contrast failing, keyboard traps. We've turned that scan into a measurement, per criterion, that runs in CI."

## Scene 2 — The design system, with Odia (90 seconds)

Open Storybook or a live preview of `@aaas/ui`. Put an Odia heading and an Odia paragraph on screen — something realistic like an admissions-form label.

> "This is our answer. Every component in this library passes WCAG 2.2 AA — and AAA on colour contrast — at commit time. Here's the button with an Odia label. Keyboard-reachable, visible focus ring, 44-pixel touch target, Noto Sans Oriya rendering all the conjuncts cleanly. Works in three themes and a dyslexia mode that knows it's looking at Odia, not Latin. We wrote 15 automated tests that fail the build if any of those regress."

Toggle dark, high-contrast, dyslexia themes live using `[data-theme]`, `[data-reading]`, and `lang='or'` attributes on the body. Narrate as the page shifts — show how Odia line-height bumps from 1.7 to 1.9 in dyslexia mode while letter-spacing stays at zero.

## Scene 3 — The roadmap (45 seconds)

Open the PLAN.md or a single slide with the six phases.

> "Phase 0 is done — what I just showed you. Plus our Odia language strategy, which is documented in the repo. Phase 1 is the multi-tenant gateway. Phase 3 is the Indic AI stack — IndicConformer and Indic-TTS for Odia first, then Hindi and 10 more languages. All on-prem, runs at OCAC's data centre. The repo is Apache-2.0, and the threat model, DPDP data-flow, and WCAG checklist are already written."

## Scene 4 — Close (15 seconds)

> "We're building accessibility as infrastructure, not as a product — for Odisha first. Foundations are in. We want one pilot institution in the state."

---

# Fallback plans

Rehearse these. You will need at least one.

## Wi-Fi dies

Everything runs locally. `pnpm dev` in the repo brings up the full stack on `localhost`. If you didn't already, start it **before judges arrive** and keep the tabs open.

## The widget breaks mid-demo

Do not debug live. Say:
> "Let me show you the recorded run — this is the same flow in our integration environment."

Switch to the hidden recording tab. Continue narration as if it were live. Recover.

## The AI service times out

Say:
> "The model server is under load — one moment, I'll switch to the scripted run."

Same move: hidden recording tab. Do not apologise repeatedly. One acknowledgment, then move on.

## Judge asks a question mid-scene

Pause, answer, return. Never race through a scene because you're worried about time. A judge interrupting is a **good sign** — they are engaged. Lean in.

## Laptop dies / projector fails

Hand the judge the printed one-page brief. Pivot to the 60-second verbal pitch. Do not try to fix hardware while they wait.

## The mic fails (Scene 2)

Type the Odia query into the widget's text input instead of speaking. Say:
> "The mic's cutting out — typed input in Odia works the same way."

## The native Odia speaker on the team is absent

If the only Odia speaker on the team can't present on demo day:
- Play a **pre-recorded Odia voice sample** (recorded during rehearsal by the Odia speaker) instead of speaking live.
- Say: *"Letting the recorded voice drive the widget — that's our teammate Priyadarshini; she's our language lead."*
- Do not attempt Odia pronunciation if you are not confident. A bad accent undermines the whole Odia-first positioning. An honest pre-recorded sample is infinitely better.

---

# Rehearsal checklist

Do each of these at least twice before demo day.

- [ ] Full-Vision run, start to finish, with a timer. Target: 6:00.
- [ ] Foundation run, start to finish, with a timer. Target: 3:30.
- [ ] Wi-Fi-off rehearsal (turn it off, run the full thing on localhost).
- [ ] One rehearsal with someone watching who hasn't seen it before. Ask them what was confusing.
- [ ] **Odia pronunciation check with a native Odia speaker** — mandatory. If no one on the team speaks Odia, find a friend / family / colleague to review before demo day. Mispronouncing ନମସ୍କାର in an Odisha hackathon room loses the room instantly.
- [ ] Have the Odia script of Scene 2 printed and on the table as a cue card.
- [ ] Speaking volume test — booths are loud; project from the diaphragm.

---

# Presenter behaviour during the demo

- **Slow down.** Your rehearsed pace is 20% too fast under adrenaline. Force a one-second pause between scenes.
- **Don't read the screen.** If a judge can read it, you don't need to say it. Narrate the *why*, not the *what*.
- **Hands off the keyboard when you're talking.** Talk, then click. Clicking while talking looks nervous.
- **Never say "simple" or "easy".** Accessibility is never simple, and judges know it.
- **If something breaks, say "let me show you the scripted version" once** — no apologies, no visible panic.
- **End by shutting up.** The worst demos keep pitching past the close. After "happy to go deep on any of it", stop talking and let them ask.
