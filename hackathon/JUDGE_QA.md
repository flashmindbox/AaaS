# AaaS — Judge Q&A Prep

Every answer below is written to be spoken in 15–45 seconds. If you start to ramble, stop. Judges prefer a crisp "I don't know — we plan to find out" over a two-minute improvisation.

Questions are grouped by what the judge is really probing for. Under pressure, identify the *type* of question first, then pull the answer.

---

## Category 0 — "Why Odisha? Why Odia?"

These are the most common opening questions at an Odisha hackathon. Nail these and the rest of the conversation goes easier.

### Q. Why Odisha first? Hindi has more speakers.

**A.** Three reasons. One — Odisha has an *active digital-service mandate* the state is held publicly accountable to. 5T and Mo Sarkar are real programmes with real political weight behind accessibility. Delhi and Mumbai don't have comparable mandates at the state level. Two — Odia is *under-served* by global tooling. Whisper's Odia WER is 25–35%; AI4Bharat's IndicConformer gets us to 12–18%. That gap is the work most projects skip; we're doing it. Three — the team has presence in Odisha. Infrastructure adoption is relationship-driven. We start where we can credibly land a pilot.

### Q. How does this fit with 5T and Mo Sarkar?

**A.** 5T's five pillars — Transparency, Technology, Teamwork, Time-limit, Transformation — all apply to a citizen being able to *actually use* a government service. A compliance dashboard visible to the IT Secretary gives 5T transparent, measurable accessibility data. Mo Sarkar asks citizens if they got what they came for; for an Odia-speaking disabled citizen today on a state portal, the answer is "no". We make the answer "yes".

### Q. How would an Odisha institution actually adopt this?

**A.** We are targeting three paths in parallel. One — bottom-up, through a single registrar or IT cell at Utkal, IIT Bhubaneswar, or NIT Rourkela, where a motivated officer can mandate the widget on their own site. Two — through OCAC, the state IT agency, which operates many citizen portals on shared infrastructure; one deployment there touches many services at once. Three — top-down, through the 5T cell or IT Secretariat, positioned as state-level policy. The first pilot we're pursuing is an Odisha state university admissions portal.

### Q. Does Odia have enough digital content to train on?

**A.** IndicCorp has meaningful Odia data — it's one of AI4Bharat's supported languages. The models we use are already trained on it. What's *thin* is dyslexia research in Odia script, regional-dialect ASR data, and Odia-specific UX conventions. We flag those as research tracks, not as claims.

### Q. Odia is a classical language — do you have cultural-sensitivity considerations?

**A.** Yes, and we've built this into the product. Government UI uses the formal ଆପଣ, not ତୁମେ or ତୁ — respectful address is the norm. Error messages are polite ("ଦୟାକରି ଦିଅନ୍ତୁ"), not imperative. Temple-service or welfare-scheme UIs that need Odia Panji dates can show them alongside Gregorian. These aren't decorative touches; they are what separates Odia-respectful from Odia-as-afterthought.

### Q. Why not also start with Bengali? Similar scripts, overlap with Odisha.

**A.** Deliberate focus. Odisha is one state with one dominant language, one IT agency, one 5T programme to align with. Adding Bengali adds West Bengal and Bangladesh complexity. Once we ship the Odia pipeline cleanly, Bengali is a straightforward extension — the fonts are similar, IndicTrans2 covers both, Indic-TTS has Bengali voices. Phase 2 plan.

### Q. What if the Odisha Government says "build this for us, keep it closed"?

**A.** We'd decline. The open-source licence is the point. A closed fork owned by one state is back to the per-institution problem. We'd happily run the pilot, deliver the value, and take feedback — but the code stays Apache-2.0 and the governance stays open. Transparency is one of 5T's five pillars; a closed-source accessibility tool contradicts the programme itself.

---

## Category 1 — "Is this actually different from what exists?"

### Q. Isn't this just another AccessiBe / UserWay / EqualWeb overlay?

**A.** No, and it's important to get this right. Those are remediation overlays — JavaScript that scans bad HTML and tries to fix it at runtime. The disability community has been clear: overlays don't work, and there's an open letter signed by hundreds of accessibility experts documenting why. We are two things those products are not: (1) a *design system* institutions build into their site, so there's nothing to remediate, and (2) an *assistive services layer* — voice, translation, captions — that the end-user chooses to turn on, not a band-aid forced on top of broken markup.

### Q. Why not just use WAVE or axe or Lighthouse?

**A.** We use axe — it's the engine inside `@aaas/a11y-test`. Those tools are diagnostic. We add three things on top: a WCAG 2.2 criterion-level machine-readable checklist, a CI-native workflow, and a multi-tenant dashboard that trends compliance over time. And we pair the measurement with the *fix* — our design system.

### Q. There are Indian accessibility startups already. Why another?

**A.** Name-check the ones the judge mentions if they name them. Our three structural differences: we are open source, on-prem-first, and built for public institutions rather than private e-commerce. If a state government adopts us, they own the deployment and the data. No vendor lock-in.

### Q. What's novel here? This looks like a collection of existing pieces.

**A.** The novelty is the *assembly*, not any single piece. Shared digital public infrastructure is, by design, made from known parts — UPI is built on ISO 20022 and bog-standard banking rails. The innovation is that nobody has assembled accessibility, Indic AI, and DPDP-grade data controls into one opinionated, open-source stack that a public institution can run on a single VM.

---

## Category 2 — "Is this technically credible?"

### Q. How does the multi-tenant isolation actually work?

**A.** Row-level security in Postgres keyed by `tenant_id`, with per-request JWT validation at the gateway setting the Postgres session context. Object storage is bucket-per-tenant in MinIO. AI inference is stateless. We also have a per-tenant encryption-key strategy in the Phase 4 plan for data at rest.

### Q. How do you handle 10 million users?

**A.** Honestly — we don't today. What we've architected for is horizontal scaling of the stateless pieces (gateway, AI inference workers) and read replicas on Postgres. The bottleneck at scale is GPU for the Indic AI services — our plan is to batch inference at the edge and cache common translations. We have a real answer for 100,000 concurrent users; beyond that we need a pilot to learn.

### Q. Which speech model? Why IndicConformer for Odia?

**A.** For Odia specifically, AI4Bharat's IndicConformer — ~12–18% WER on Odia, versus ~25–35% for Whisper-large. IndicConformer is trained on IndicCorp, which includes Odia, and it's genuinely better for the language we lead with. For Hindi and some other high-resource Indic languages we may still use Whisper-medium; the routing happens at the `/stt` endpoint by language. Our TTS is AI4Bharat's Indic-TTS for Odia (Piper has zero Odia voices; it's not an option).

### Q. How good is Odia ASR really? Have you tested it with rural accents?

**A.** Honest answer: not yet in depth. IndicConformer's benchmark numbers are on standard Odia, closer to Bhubaneswar / Cuttack speech. We know accuracy will drop on Kosali, Sambalpuri, and Desia dialects common in western and southern Odisha. Phase 3 includes a dialect-robustness benchmark and a plan to fine-tune on regional recordings — we'd want to do that in partnership with an Odisha university's linguistics department.

### Q. What about latency for voice interaction?

**A.** Round-trip budget is 1.5 seconds end-to-end for the Odia voice scene. Measured ~1.3 seconds on a single A10 GPU: IndicConformer streaming 300 ms first-token, Indic-TTS 200 ms first audio, network on LAN negligible. For Hindi/English the pipeline is lighter. Translation adds ~300 ms but is cached for frequent government-form phrases at tenant onboarding.

### Q. What happens if the AI service is down?

**A.** The design system still works — that's why we split the layers. Assistive services are an enhancement, not a dependency. The widget degrades to a text-only mode with the keyboard-accessible form. Nothing the user can do today stops working.

### Q. Security model?

**A.** STRIDE threat model per component, written up in `docs/threat-model.md`. Mutual TLS inside the stack, rate-limited API gateway, Keycloak for tenant auth with short-lived JWTs, audit log with a Postgres trigger that blocks updates, CycloneDX SBOM generated on every CI run with Grype scanning. Phase 0 residual risks are documented — we don't have DDoS mitigation or a secrets-rotation pipeline yet; both are on the Phase 5 list.

---

## Category 3 — "Does the social impact claim hold up?"

### Q. Isn't this patronising? People with disabilities don't need a widget, they need better-built websites.

**A.** They need both. The widget is explicitly opt-in and gives the user *control* — they pick their language, their reading mode, their voice-or-text preference. Nothing is imposed. And the design-system half of AaaS is exactly the "build better websites" answer — that's why we ship both layers. We won't claim the widget replaces good HTML. It supplements it.

### Q. How do you involve disabled users in the design?

**A.** Phase 5 of our plan is a structured user-testing programme with the National Association for the Blind and Enabling Unit partners at three universities we've identified. Today, Phase 0, we've built against WCAG 2.2 AA and the accepted best practices; we know that's necessary but not sufficient. Real lived-experience feedback starts at Phase 2.

### Q. What about people without smartphones or reliable internet?

**A.** Two answers. One — the compliance scorecard and design system help on *any* device: feature phones accessing a well-built site still benefit. Two — Phase 5 has a kiosk mode and an SMS-channel fallback for form filling, specifically for rural and low-connectivity contexts. That said, the voice/AI services do need connectivity and a modern browser. We don't solve the digital divide; we try not to make it worse.

### Q. Isn't sign language more important than captions?

**A.** For many Deaf users, yes. Native Indian Sign Language matters more than captions, because ISL is a different grammar from Hindi or English. Phase 5 includes an ISL avatar track — we're in touch with the ISLRTC in Delhi about corpus access. Captions are Phase 3 because they're technically easier; the ISL work is hard and we're honest that it's later.

---

## Category 4 — "Who pays for this? Is this sustainable?"

### Q. What's the business model?

**A.** It's open source, Apache-2.0 — institutions deploy it themselves, free. Sustainability comes from three places: (1) a paid managed-hosting option for institutions that don't want to run it themselves, (2) government grants under the DPI playbook (MeitY, National Centre for Accessibility), and (3) CSR funding from companies with digital-accessibility compliance obligations. We're modelled on organisations like MOSIP, not on SaaS startups.

### Q. Why would a government university actually adopt this?

**A.** Three reasons. One — they're legally required to be accessible under the RPwD Act and currently non-compliant. Two — a new UGC circular tied accessibility to institutional ranking, and Odisha state universities are under 5T scrutiny separately. Three — once one high-profile institution adopts it, peer adoption follows; in Odisha our first-pilot targets are IIT Bhubaneswar, Utkal University, or NIT Rourkela, because "what IIT Bhubaneswar uses" is a valid answer for the next BPUT-affiliated college.

### Q. How do you compete with free ChatGPT doing the same thing?

**A.** Two reasons a chatbot isn't the answer. One — DPDP and data residency. A public institution cannot legally send applicant speech data to OpenAI's servers. Two — integration: ChatGPT can read the page, but it can't reliably *drive* the form. Our widget has structured access to the DOM via the institution's integration.

### Q. Five-year vision if this works?

**A.** Two outcomes. One — this becomes part of the digital-public-infrastructure stack alongside DigiLocker, e-Sign, and UPI — an accessibility layer any service of the government of India can attach to. Two — we scale beyond universities: municipal services, state portals, exam conducting bodies. The per-tenant cost should trend to effectively zero because of shared infra.

---

## Category 5 — "Why you?"

### Q. Why is your team the right one to build this?

**A.** *(Customise with real team backgrounds.)* We're a cross-disciplinary team — engineering, design, and policy. Between us we've worked on [specific prior projects relevant to govt, accessibility, or Indic tech]. We named the team SUBARNAREKHA — the river that connects eastern Indian states — because this is an infrastructure bet and the metaphor is deliberate.

### Q. Do you have accessibility expertise on the team?

**A.** *(Be honest.)* We have strong engineering, and we've built against the WCAG 2.2 AA spec from day one — colour contrast, keyboard nav, focus management, screen-reader landmarks. We do not yet have a professionally trained accessibility auditor on the core team. That's one of our explicit Phase 2 hires / advisors we're looking for — and it's a question we'd welcome a judge's help on.

### Q. What happens after the hackathon — is this a real project or just a weekend hack?

**A.** Real project. The repo is already Apache-2.0, the roadmap is documented through six phases, and we've scoped the Phase 0 exit gate at "any contributor can run the stack in 10 minutes" specifically because we need external contributors. We've identified three universities willing to pilot. Hackathon or not, we ship.

---

## Category 6 — The tough / sceptical questions

### Q. You listed IndicTrans2 and Whisper — those aren't yours. Where's the actual innovation?

**A.** Fair. The innovation is not in the individual models. It's in the *integration layer* — the design system, the measurement harness, the multi-tenant control plane, the DPDP data-flow controls. If a judge insists on model-level innovation, we don't have any and we won't claim it. We're doing the unglamorous integration work that turns research models into deployable public infrastructure. That is the work most projects skip.

### Q. Can you really make a single framework accessible to dyslexic, blind, Deaf, and low-literacy users at once?

**A.** Honestly, trade-offs exist. Dyslexia-friendly fonts can interfere with screen readers if implemented naively; we use `aria-label` to preserve semantic text. High contrast for low-vision can hurt readability for some photophobic users; that's why we expose the choice rather than impose it. We've made the trade-offs visible, not hidden. Some users will always need assistive tech we haven't built yet — we don't claim universality.

### Q. What stops a private company from forking this and commercialising it?

**A.** Nothing. Apache-2.0 permits that. That's deliberate — we want adoption. Our moat, if we need one, is being the trusted reference implementation that governments pick because it's the original and it's politically neutral. That's the MOSIP model.

### Q. You're at Phase 0. How do I know Phases 1–6 aren't vapour?

**A.** You don't, and you shouldn't take our word for it. What you can check: (1) the repository has the plan, the threat model, the DPDP doc, the WCAG checklist, CI, SBOM — all of that is real work, not slides. (2) Phase 0 was scoped to a non-trivial exit gate that we met. (3) We've broken the rest into phases small enough to evaluate independently. Follow the repo; Phase 1 will either land or it won't.

### Q. Why should we pick you over the three other hackathon teams building accessibility tools?

**A.** Probably you should talk to all of us and compare. What I'd say is: we're the only one positioning this as *shared public infrastructure* rather than a product, the only one with an end-to-end DPDP data-flow already written, and the only one that's shipped something you can `git clone` today. Those might be the right filters, or you might have others. We'd welcome feedback either way.

---

## Answering patterns — how to handle questions well

- **If you don't know:** "Honestly, I don't know. Here's how we'd find out: [next step]."
- **If the question reveals a weakness:** Acknowledge it first. "That's a real gap. Here's what we're doing about it: [specific]."
- **If the question is based on a wrong assumption:** Correct it gently and briefly, then answer. Don't spend a minute correcting.
- **If it's hostile:** Stay calm, stay short, thank them for the challenge. Hostile questions often become the judge's favourite moment later.
- **If you've already answered it:** "As I mentioned — short version: [10-word re-answer]." Don't re-argue.

## What to do after the Q&A

Write down every question that stumped you. By the next round of interviews you'll have five more answers rehearsed.
