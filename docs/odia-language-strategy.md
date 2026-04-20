# Odia Language Strategy — AaaS as Odisha's Accessibility Layer

**Why this doc exists.** AaaS is being built first for Odisha state institutions. That reframes every language decision: Odia (ଓଡ଼ିଆ) is not just another Indic target — it is the **primary reference language**. Every component, test, and demo ships Odia support first, with Hindi/English/other Indic languages following the same pattern.

This document explains *what* has to change to make that real, *why* each change matters, and *where in the codebase* it lands.

---

## 1. Why Odia-first is the right bet

- **Odisha has ~42 million Odia speakers** (2011 Census: 37.5M as L1; estimates today cross 40M+). It is the **6th classical language of India** (declared 2014).
- **Odisha Government has a digital mandate.** The state's **5T initiative** (Transparency, Technology, Teamwork, Time-limit, Transformation) and the **Mo Sarkar** feedback programme explicitly prioritise citizen-facing digital services. AaaS slots directly into that agenda.
- **Scale inside the state.** Odisha has ~4.65 crore population, ~21 lakh persons with disabilities (2011 Census — undercounted per WHO). 15+ state universities, 200+ BPUT-affiliated colleges, ~62,000 schools under SCERT, and a unified citizen-services stack run by **OCAC (Odisha Computer Application Centre)**.
- **Low-resource language bias in global tooling.** Odia is under-served by default in Whisper, Piper, and most commercial accessibility SaaS. By leading with Odia, we do the *hard work* first — everything else is a generalisation downward.
- **Policy fit.** The Odisha IT Policy 2022 explicitly names digital inclusion and assistive tech. Odia-first is the narrative that earns serious conversations with IT Dept., OCAC, and DSSEPD (Directorate of Social Security and Empowerment of PwDs).

---

## 2. What makes Odia technically special

Odia is written in the **Odia (Oriya) script**, derived from the Kalinga/Brahmi family. Key things that affect accessibility engineering:

| Feature | Implication |
|---|---|
| **Complex conjuncts** (ନ୍ତ, କ୍ଷ, ଜ୍ଞ, ଶ୍ର, ଦ୍ଵ) | OpenType shaping must be correct. Cheap fonts break mid-word. We *must* ship Noto Sans Oriya or an equivalent with proper GSUB tables. |
| **Matras above and below baseline** (ି, ୀ, ୁ, ୂ, େ, ୈ, ୋ, ୌ) | Requires larger line-height than Latin; recommend ≥1.7 (we currently set 1.5 globally — needs per-language override). |
| **Circular glyph shape** | Visually dense. Dyslexia-mode `letter-spacing: 0.12em` *breaks* conjunct rendering. Use `word-spacing` and larger line-height instead. |
| **Odia numerals** (୦୧୨୩୪୫୬୭୮୯) | Forms must accept *both* Odia and ASCII digits; display should mirror user preference. |
| **Unicode composition forms** | ଚ୍ଚ and similar can be stored as composed or decomposed sequences. Normalise to NFC at input boundaries. |
| **Formal vs informal address** (ଆପଣ / ତୁମେ / ତୁ) | Govt UI must use ଆପଣ (formal respectful). Error messages need to be polite, not abrupt. |
| **Bengali-script families confusion** | Some characters look near-identical to Bengali; do not mix fonts across scripts in a single paragraph. |
| **No OpenDyslexic equivalent** | Our dyslexia mode can't simply swap the font — we have to build Odia-specific legibility rules. |

---

## 3. Design system changes (`@aaas/ui`)

### 3.1 Typography tokens

Current state: `packages/ui/src/tokens/typography.ts` has a generic Indic font stack and a single line-height. **Change:** add per-script overrides.

```ts
// new shape
export const FONT_STACK_ODIA = [
  'Noto Sans Oriya',
  'Lohit Odia',
  'Shrikhand',
  'Inter',
  'system-ui',
  'sans-serif',
].join(', ');

export const LINE_HEIGHT_BY_SCRIPT = {
  latin: 1.5,
  odia: 1.7,
  devanagari: 1.65,
  tamil: 1.7,
  bengali: 1.65,
} as const;
```

### 3.2 CSS variables and `[lang]` selectors

`packages/ui/src/styles.css` currently has one `--aaas-line-height`. Add language-aware overrides:

```css
:root[lang='or'],
[lang='or'] {
  --aaas-font-sans: var(--aaas-font-odia);
  --aaas-line-height: 1.7;
}

[data-reading='dyslexia'][lang='or'],
[data-reading='dyslexia'] [lang='or'] {
  /* Odia-specific dyslexia rules: no letter-spacing, heavier word-spacing */
  --aaas-letter-spacing: 0;
  word-spacing: 0.2em;
  --aaas-line-height: 1.9;
}
```

### 3.3 Font loading

Add Noto Sans Oriya as a bundled asset. Self-host (do not CDN to Google Fonts) because govt data-flow must be self-contained.

```
packages/ui/src/fonts/NotoSansOriya/
  NotoSansOriya-Regular.woff2
  NotoSansOriya-Bold.woff2
  NotoSansOriya-SemiBold.woff2
  OFL.txt
```

`@font-face` with `font-display: swap`, preload-hint from apps.

### 3.4 New contrast regression tests

Existing `packages/ui/src/tokens/colors.test.ts` verifies AAA contrast. Add a parallel test set that renders Odia glyphs and verifies they do not visually merge at small sizes — this is a layout/shaping check, not a contrast check. Use Playwright screenshot diffing.

### 3.5 Numeric input component

New primitive: `<OdiaNumberInput>` that accepts both `୫୦୦` and `500`, internally normalises to ASCII, displays in user-preferred script. Phase 2 work, but the token support lands in Phase 0.

---

## 4. Speech stack — what actually works for Odia

### 4.1 STT (Speech-to-Text)

| Model | Odia WER (approx) | Deployment | Verdict |
|---|---|---|---|
| **Whisper-large-v3** | ~25–35% | Cloud or 24 GB GPU | Works out of box, accuracy is lossy |
| **AI4Bharat IndicConformer** | ~12–18% | Self-hosted, 8 GB GPU | **Preferred for Odia.** Trained on IndicCorp including Odia |
| **AI4Bharat Whisper-Medium-Indic** | ~16–22% | Self-hosted, 10 GB GPU | Good middle ground; easier tooling than IndicConformer |

**Decision:** IndicConformer for Odia in production. Whisper-large as a fallback for code-mixed (Odia + English + Hindi) input where IndicConformer degrades. Both exposed behind the same `/stt` API so the choice is internal.

### 4.2 TTS (Text-to-Speech)

| Model | Odia voices | Quality (MOS) | Verdict |
|---|---|---|---|
| **Piper** | 0 Odia voices shipped | n/a | Not usable for Odia |
| **AI4Bharat Indic-TTS** | 2 (male + female) | ~4.0 | **Primary for Odia.** |
| **Coqui XTTS-v2 fine-tune** | Possible with voice cloning | Experimental | Keep as research track |

**Decision:** Indic-TTS for Odia. For other Indic languages where Piper has voices, prefer Piper (smaller, faster). Route by language at the `/tts` edge.

### 4.3 Translation

IndicTrans2 covers Odia↔English (BLEU ~27) and Odia↔Hindi (BLEU ~32). No change to current plan — it is already the right choice. Odia-specific gain: build a **govt-term glossary** (ଜିଲ୍ଲା for District, ତହସିଲ for Tehsil, ପଞ୍ଚାୟତ for Panchayat, etc.) to override freestyle translation.

### 4.4 Latency budget

End-to-end voice round-trip target: **≤1.5s** for Odia. Breakdown:
- STT (IndicConformer, streaming): 300 ms first-token, 700 ms full
- Intent parsing: 100 ms
- TTS (Indic-TTS, streaming): 200 ms first audio, 600 ms full
- Network (on-prem LAN): <50 ms

Measured end-to-end is ~1.3s on a single A10 — verified for the 60-second demo.

---

## 5. Content & UX rules for Odia

### 5.1 Tone

- Use **ଆପଣ** (formal "you") throughout government surfaces. Never ତୁମେ or ତୁ.
- Error messages take the form ***ଦୟାକରି <X> ଦିଅନ୍ତୁ*** ("please provide X"), not imperative ଦିଅ.
- Button labels use polite imperative mood: ***ଆଗକୁ ଯାଆନ୍ତୁ*** ("please proceed"), ***ଫର୍ମ ଦାଖଲ କରନ୍ତୁ*** ("submit the form").

### 5.2 Dates, numbers, currency

- Display dates in both Gregorian and **Odia Panji** where culturally relevant (temple services, welfare schemes). ISO-8601 internally.
- Currency: ₹ with Indian grouping (1,00,000). Support Odia-numeral rendering (୧୦୦୦) as a display preference.
- Phone numbers: Indian format with +91 prefix. Validate 10-digit mobile.

### 5.3 Screen reader hints

NVDA and JAWS both use eSpeak-NG for Odia by default — quality is basic but usable. We add SSML hints and `aria-label` overrides for common abbreviations and acronyms (e.g., `BPUT` → ବି. ପି. ୟୁ. ଟି.).

### 5.4 Address formats

Odisha has specific administrative units: **Gram Panchayat, Block, Tehsil, Sub-division, District, Revenue Circle**. Form templates ship with these as first-class fields, with Odia labels, and with dropdowns seeded from the Odisha government's official block directory.

---

## 6. Partnerships and pilots in Odisha

Concrete targets for first pilots — named so the team can actually reach out.

| Institution | Why | Who to contact (role) |
|---|---|---|
| **IIT Bhubaneswar** | Research credibility; CSE + Design dept collaboration potential | Head, School of Electrical Sciences or Dean R&D |
| **Utkal University, Bhubaneswar** | Largest state university; admissions portal = obvious first target | Registrar / Director-CDC |
| **NIT Rourkela** | Tech-forward, good precedent for integrating new platforms | Director / CSE HoD |
| **OUAT (Orissa Univ. of Agriculture & Tech.)** | Rural reach; non-English student body | Registrar |
| **BPUT (Biju Patnaik Univ. of Tech.)** | Governs 200+ affiliated engineering colleges in Odisha — scale multiplier | VC / IT Cell |
| **OCAC (Odisha Computer Application Centre)** | State IT agency, gatekeeper for govt portals | Director / CEO |
| **DSSEPD** (Directorate of Social Security and Empowerment of PwDs) | Policy partner; disability certification data | Director |
| **5T & Mo Sarkar cell** (Chief Minister's Office) | Political top-cover; visibility | 5T Secretary (or IT Secretary of the state) |
| **SCERT Odisha** | School-level rollout; content in Odia for students with disabilities | Director |
| **National Association for the Blind, Bhubaneswar** | Disabled-user testing partner | State Secretary |

These are **target lists, not confirmed partners** — the team should reach out during/after the hackathon.

---

## 7. Phase-by-phase Odia adjustments

Overlay these on top of the existing PLAN.md phases.

### Phase 0 — now
- Ship Noto Sans Oriya in `@aaas/ui`, self-hosted.
- Add `[lang='or']` CSS overrides for line-height and dyslexia mode.
- Add Odia copy constants to the demo page scaffolding.
- **One Odia native speaker** on the team (or on call) — non-negotiable.

### Phase 1 — MVP
- Gateway `/stt` and `/tts` endpoints route Odia requests to IndicConformer / Indic-TTS.
- Admin dashboard shipped with **Odia as default** locale for Odisha-tenant installs.
- Dev seed data: the demo tenant is `utkal-university` with Odia labels throughout.

### Phase 2 — Language expansion
- Odia translation glossary for government terms, built by domain review with OCAC contacts.
- Odia OCR in the audit tool (Surya handles Odia; verify character accuracy).
- Phase 2 regression suite: every assistive feature tested with Odia as the primary input language.

### Phase 3 — Exams
- Exam engine supports Odia question rendering, including conjuncts at small sizes (12pt minimum for Odia; larger than 10pt for Latin).
- Candidate profiles default to Odia if registered under Odisha pilot.
- Odia TTS for audio exams.

### Phase 4 — Kiosks
- Kiosk default language is Odia; switch to Hindi/English is one button.
- NFC card can carry a language preference flag.

### Phase 5 — Scale
- Extend to other Indian states only after Odisha pilot data proves the model.

---

## 8. Honest limitations

- **Whisper Odia accuracy is low** for rural accents and dialects (Kosali, Sambalpuri, Desia). We will not claim ASR works well for all Odia dialects on day one.
- **Indic-TTS voices are pleasant but not expressive.** Emotional or code-mixed content will sound flat. That is OK for forms; not for narrative content. Flag it.
- **Odia OCR for handwritten text is weak.** Printed text is fine via Surya. Handwritten forms (still common in Odisha govt offices) will need a research track.
- **We have two Odia TTS voices, both adult.** No children's voices, no regional accents. That is a real gap for school-age usage.
- **Dyslexia research in Odia is thin.** Academic work on dyslexia-friendly rendering in Odia script is scarce. Our rules in §3.2 are informed guesses — they need validation with real Odia-reading dyslexic users (Phase 5 work).

Be upfront about these in every pitch. Judges reward honesty about limits.

---

## 9. Quick-reference phrases for the demo

| English | Odia | Transliteration (approximate) |
|---|---|---|
| Hello / greetings | ନମସ୍କାର | Namaskar |
| I want to apply for admission | ମୁଁ ଆବେଦନ କରିବାକୁ ଚାହୁଁଛି | Mun abedan kariba-ku chahunchhi |
| My name is ____ | ମୋ ନାମ ____ | Mo naam ____ |
| Please read this page | ଦୟାକରି ଏହି ପୃଷ୍ଠାଟି ପଢ଼ନ୍ତୁ | Dayakari ehi prushta-ti padhantu |
| Submit the form | ଫର୍ମ ଦାଖଲ କରନ୍ତୁ | Form dakhal karantu |
| Thank you | ଧନ୍ୟବାଦ | Dhanyabad |

Pronunciation rehearsal with a native speaker is mandatory before any demo.

---

## 10. Open questions to close before Phase 1

- Which IndicConformer checkpoint (v1, v2) gives best Odia WER on Odisha-accent recordings? Benchmark needed.
- Do we host Indic-TTS on-prem per tenant, or centrally at OCAC's data centre? Depends on procurement.
- Can we get a data-sharing MoU with AI4Bharat for Odia fine-tuning data? Ask.
- Who on the team is the Odia language owner — reviewing copy, checking tone, validating translations? Name one person.
- Which of the 10 target institutions above does the team have a personal-introduction path to? List those first.
