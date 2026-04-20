# Presenter One-Pager — Know This Cold

Carry this in your pocket. Read it five times on the train to the venue. You should be able to answer every line from memory.

---

## Identity

- **Team name:** SUBARNAREKHA — the river that flows from Jharkhand through Bengal and empties into the Bay of Bengal at Odisha's Balasore coast. Subarna = gold, Rekha = streak. The river carries gold to Odisha. We're infrastructure built *for* Odisha, flowing *from* open-source.
- **Project name:** AaaS — Accessibility as a Service — Built for Odisha, designed for every Indian public institution.
- **One-liner:** *The UPI of accessibility — Odisha first, India next. An open, shared, Odia-first layer any public institution can plug into.*
- **License:** Apache-2.0. Say this early in any conversation.

---

## What it is (30-second version)

Three layers in one open-source stack:
1. **`@aaas/ui`** — React design system. WCAG 2.2 AA by default, AAA on colour contrast. Noto Sans Oriya bundled, Odia-specific line-height and dyslexia rules.
2. **`@aaas/a11y-test`** — CI-native compliance harness built on axe-core, per-criterion reporting.
3. **The assistive widget** — Odia voice (AI4Bharat IndicConformer), translation (IndicTrans2), Odia TTS (AI4Bharat Indic-TTS), captions, dyslexia mode. All on-prem at OCAC.

---

## Numbers to memorise

**Odisha (say these first to any Odisha-audience judge)**

| What | Number |
|---|---|
| Odia speakers worldwide | ~42M (L1: ~37.5M per 2011 Census) |
| Persons with disabilities in Odisha | ~21 lakh (2011 Census — undercounted) |
| Odisha population | ~4.65 crore |
| State universities in Odisha | 15+ |
| BPUT-affiliated colleges | 200+ |
| Schools under SCERT Odisha | 62,000+ |
| Odia — declared classical language | 2014 (6th in India) |
| State IT agency | OCAC |
| State digital mandate | 5T + Mo Sarkar |

**India-wide context**

| What | Number |
|---|---|
| Indians with disabilities (conservative) | 60M+ |
| Scheduled languages in the Constitution | 22 |
| Indian languages we target in Phase 3 | 12 (Odia first) |

**Platform**

| What | Number |
|---|---|
| WCAG compliance floor | 2.2 AA |
| Colour contrast target | AAA (≥7:1) |
| Minimum touch target | 44 px (WCAG 2.5.8) |
| Line-height for Odia | ≥1.7 (vs 1.5 for Latin) |
| Voice round-trip target | ≤1.5s end-to-end |
| Licence | Apache-2.0 |

If you forget a number, say **"I want to be precise — let me check the doc"** and flip to this sheet. Fabricating numbers is worse than checking.

---

## What's built vs. what's planned — be honest

**Built (Phase 0):**
- Monorepo with strict TypeScript, CI, SBOM generation
- `@aaas/ui` design system with Button, SkipLink, VisuallyHidden, themes (light/dark/high-contrast/dyslexia)
- `@aaas/a11y-test` with axe-core harness, WCAG 2.2 criterion-level checklist, CLI
- Docker Compose dev stack (Postgres, Redis, MinIO, Keycloak, Jaeger, MailHog)
- STRIDE threat model, DPDP data-flow map, WCAG acceptance checklist
- **Odia language strategy doc** (`docs/odia-language-strategy.md`) — typography rules, STT/TTS stack, dyslexia-for-Odia, pilot partner list

**Planned (Phases 1–6):**
- Phase 1: multi-tenant auth, API gateway, tenant admin
- Phase 2: embed widget MVP, per-tenant JS snippet
- Phase 3: Indic AI services (the demo-visible magic)
- Phase 4: compliance dashboard
- Phase 5: exam mode, kiosk mode, ISL avatar
- Phase 6: polish, mobile SDKs, observability, open-source release

If a judge asks "is this done?", the answer is **"Phase 0 is done — the foundations, harness, and dev stack. Phases 1 through 6 are scoped with an exit gate each."**

---

## Our differentiation — memorise three

1. **Infrastructure, not a product.** Shared public good, not a SaaS add-on. Modelled on MOSIP.
2. **Odia-first, not Hindi-first-and-Odia-later.** Typography tuned for Odia. STT via IndicConformer (not Whisper) because it's actually better for Odia. Built for Odisha's scale, not a translation target of a Delhi roadmap.
3. **On-prem at OCAC, DPDP-compliant.** Data never leaves Odisha. Every commercial competitor is cloud-hosted and ships speech samples overseas.

If you can only say one thing in a hallway pitch, say #2 — that's what makes us local to this room.

---

## Where we are weak — don't hide it

- **No professionally trained accessibility auditor on the team yet.** Actively looking. If a judge is one, that's a lead.
- **Not tested with disabled Odia-speaking users yet.** Phase 5. The most important validation, deliberately sequenced late so we don't test a half-built product. The National Association for the Blind's Bhubaneswar chapter is our target partner.
- **No pilot institution signed in Odisha.** We have a target list (Utkal, IIT Bhubaneswar, NIT Rourkela, OUAT, BPUT, OCAC). Nothing on paper yet.
- **Odia ASR for rural dialects (Kosali, Sambalpuri, Desia) is unproven.** IndicConformer is good for standard Odia; western/southern Odisha dialects need a dataset we don't have yet.
- **Phase 3 is the hard phase.** Indic AI models are large and deployment is non-trivial. We have a plan and latency numbers on a reference GPU, not a running service in production.

**Say these weaknesses honestly if asked.** Judges can smell defensiveness. They respect teams who know their own gaps.

---

## The four questions a judge most often asks

Rehearse these answers until you can say them in your sleep:

1. *"Why Odisha first? Why Odia?"*
   → Odisha has the 5T + Mo Sarkar digital mandate, Odia is under-served by global tooling (IndicConformer beats Whisper on Odia by 10+ WER points), and we have credible adoption paths through OCAC, Utkal, IIT Bhubaneswar. Starting where we can land the first pilot.

2. *"How is this different from an accessibility overlay?"*
   → Not a remediation overlay. We're a design system institutions build *into* their sites, plus an assistive services layer users *opt into*. Overlays are criticised; we're not one.

3. *"Why would a government institution adopt this?"*
   → Legal requirement under RPwD Act, UGC ranking tie-in, 5T scrutiny in Odisha, and zero vendor lock-in because it's Apache-2.0 and on-prem at OCAC.

4. *"What's the business model?"*
   → Open source with optional paid hosting. Grants and CSR, not SaaS. Modelled on MOSIP and DigiLocker.

5. *"Why you?"*
   → Cross-disciplinary team, Odisha-rooted. Working code and an Odia-language strategy doc on day one. Shipping infrastructure, not a pitch deck. *(Then say something true and specific about your team.)*

---

## Phrases that win the room

- "Odisha first, India next"
- "Aligned with 5T and Mo Sarkar"
- "Odia as the reference language, not a translation target"
- "Digital public infrastructure — on-prem at OCAC"
- "Built into the component, not bolted onto the page"
- "Apache-2.0, open contributions, pilot-ready"
- "ଓଡ଼ିଶା ପାଇଁ, ଓଡ଼ିଶା ଠାରୁ।" (open an Odia-speaking audience with this)

## Phrases to never say

- "Overlay" (unless you're explaining what we're *not*)
- "Solves accessibility"
- "AI-powered" without naming the model
- "Disruptive" — this isn't a startup pitch, it's infrastructure
- "Obviously" — nothing about accessibility is obvious

---

## Presenter etiquette

- **Stand up, don't sit, when a judge walks up.** Eye level matters.
- **Hand them a card or QR code within the first 20 seconds.** They have 40 other booths to visit.
- **Don't interrupt their questions.** Let them finish. Count to one.
- **If two teammates are present, decide in advance who speaks first.** Second teammate only adds if asked or if the first has finished.
- **End every conversation with a specific ask.** "Would you be willing to connect us to [MeitY / your a11y contact / a pilot institution]?"

---

## If you're unsure

The safe moves, in order:
1. *"Let me check the doc."* → open this sheet, PLAN.md, or `docs/odia-language-strategy.md`.
2. *"Honestly, I don't know — we'd find out by [specific next step]."*
3. *"I'll connect you with [teammate] who knows that end — can I get a card?"*

**If a judge asks you something in Odia and you're not a native speaker:** smile, say *"Let me hand you to [native-speaker teammate]"* — do not guess. If no teammate is available, say *"I'll get the exact answer back to you — may I email you?"*

Never invent a number. Never promise a feature. Never say a competitor's name negatively unprompted.

---

## Before you walk on

Three breaths. Stand straight. Smile. You built this. Go.
