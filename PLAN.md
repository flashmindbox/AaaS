# AaaS Platform — Comprehensive Build Plan

**Project:** Accessibility as a Service (AaaS) Infrastructure for Public Institutions
**Team:** SUBARNAREKHA
**Source document:** Aas.pdf
**Plan created:** 2026-04-20

---

## 1. Guiding Principles

- **Odisha first, India next.** Primary pilot state is Odisha; Odia is the reference language. Every Indic-language feature is built and validated against Odia before it ships to other languages.
- **Accessibility-first, not bolt-on** — WCAG 2.2 AA minimum, targeting AAA for core surfaces.
- **API-first** — every feature usable via REST/GraphQL + SDK before UI.
- **Multi-tenant by default** — one platform, many institutions.
- **Offline-tolerant** — kiosks and rural classrooms may lose connectivity.
- **Data sovereignty** — DPDP Act 2023 (India) compliant; data residency in-country; reference on-prem deployment at OCAC (Odisha Computer Application Centre).
- **Open models where possible** — AI4Bharat, Whisper, Piper — avoids vendor lock-in and supports Indic languages natively, with Odia-specific choices called out in `docs/odia-language-strategy.md`.

---

## 2. Target Architecture (end-state)

```
 +----------------------------------------------------------+
 | Clients: Web widget . Mobile SDK . Kiosk UI . Exam App   |
 +---------------+------------------------------------------+
                 | HTTPS / WSS
        +--------v----------+
        | Accessibility API |  Auth . Rate-limit . Routing . Audit
        |     Gateway       |
        +--------+----------+
   +-----+------+------+-------+------+-------+
   v     v      v      v       v      v       v
  STT   TTS  Translate Screen  Exam  Content  Admin
 (ASR) (Voice)  (MT)  Reader  Engine Adapter   API
   |     |      |      |       |      |       |
   +-----+------+------+-------+------+-------+
                 |
         +-------+----------+
         |  Data Plane      |  Postgres . Redis . Object store . Vector DB
         |  Model Plane     |  GPU inference (Triton/vLLM) . Model registry
         |  Observability   |  OTel . Prom . Loki . Sentry
         +------------------+
```

---

## 3. Tech Stack (locked choices)

| Layer | Choice | Why |
|---|---|---|
| Gateway | Kong + custom auth plugin | WAF, rate-limiting, OIDC built-in |
| Backend services | Python FastAPI (AI) + Go (gateway/exam) | FastAPI for ML; Go for latency-sensitive |
| Frontend | React 18 + TypeScript + Radix UI | Radix = accessible primitives out of the box |
| Widget | Preact + Shadow DOM | Tiny, isolated, no host-site CSS conflicts |
| Mobile | React Native + native modules | Single codebase, native bridges for TTS/STT |
| Kiosk | Android Kiosk Mode (primary) / Electron on Linux | Cheap hardware, Play Store updates |
| STT | **AI4Bharat IndicConformer (primary for Odia, ~12–18% WER)** + Whisper-large-v3 (fallback for code-mixed) | Best Odia accuracy; route per-language at `/stt` |
| TTS | **AI4Bharat Indic-TTS (primary for Odia; 2 voices shipped)** + Piper (non-Odia, fast edge) | Piper has zero Odia voices; Indic-TTS is mandatory for Odia |
| Translation | IndicTrans2 | SOTA for 22 scheduled Indian languages |
| OCR | EasyOCR + Surya | Multilingual, including Devanagari/Tamil/Bengali |
| LLM (simplify/summarize) | Llama 3.1 8B Indic-tuned, self-hosted | Data sovereignty |
| DB | PostgreSQL 16 + Redis + MinIO (S3) | Standard, OSS |
| Vector DB | pgvector | Fewer moving parts |
| Auth | Keycloak + DigiLocker OIDC adapter | SSO + govt identity |
| Infra | Kubernetes (EKS/AKS/on-prem Kubeadm) + Terraform | Portable — govt on-prem requirement |
| Inference | Triton Server / vLLM on NVIDIA L4/A10 | Cost/perf sweet spot |
| CI/CD | GitHub Actions + ArgoCD | GitOps |
| Monitoring | OpenTelemetry + Prometheus + Grafana + Sentry | OSS stack |

---

## 4. Phase-wise Roadmap

### Phase 0 — Foundations *(Weeks 0-2)*

Deliverables:
- Monorepo scaffold (Nx or Turborepo) with `apps/`, `services/`, `packages/`, `infra/`
- Design system package (`@aaas/ui`) on Radix with tokens (color contrast >= 7:1), **Noto Sans Oriya bundled, Odia-aware line-height and dyslexia rules**
- CI/CD: lint, typecheck, test, axe-core accessibility tests, Docker build, SBOM
- WCAG 2.2 AA acceptance checklist as a machine-enforced test suite
- Threat model (STRIDE) + DPDP Act data-flow mapping
- **Odia language strategy document** (`docs/odia-language-strategy.md`) covering typography, speech stack, dyslexia rules, pilot partners
- Dev environment via Docker Compose (Postgres, Redis, MinIO, Keycloak)

**Exit gate:** any contributor can run the whole stack locally in under 10 minutes.

---

### Phase 1 — MVP Core Services *(Weeks 3-8)*

Scope = the minimum a pilot institution can actually use on a website.

| Module | MVP feature set |
|---|---|
| API Gateway | OIDC login, API keys per tenant, rate limits, request logging |
| STT service | **Odia (IndicConformer) + English + Hindi**, file + streaming (WebSocket), < 2s latency for 10s audio |
| TTS service | **Odia (Indic-TTS) + English + Hindi**, SSML subset, MP3/Opus output, caching by hash |
| Web Accessibility Widget v1 | Floating button to panel: **Odia** TTS read-aloud (default for Odisha tenants), font size, high-contrast, Odia-aware dyslexia mode, keyboard-only mode |
| Admin Dashboard v1 | Tenant onboarding, API key mgmt, usage metrics, audit log viewer, **Odia as default locale for Odisha-tenant installs** |
| JS SDK | `<script>` one-liner install; honors `prefers-reduced-motion`, `prefers-contrast`, detects `lang="or"` |

**Exit gate:** Odisha pilot institution website (target: Utkal / IIT Bhubaneswar / NIT Rourkela) passes axe-core with 0 criticals + widget usage demo in Odia and English.

---

### Phase 2 — Language & Assistive Expansion *(Weeks 9-14)*

| Module | Additions |
|---|---|
| Translation Engine | IndicTrans2 self-hosted, 22 Indian languages, glossary support for institutional terms (**Odisha-specific govt-term glossary shipped first**) |
| STT/TTS | Odia already in Phase 1; Phase 2 adds Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Urdu, **Kosali / Sambalpuri dialect benchmarks for Odia** |
| Screen Reader Overlay | ARIA live regions, landmark navigation, skip-links injection, image alt-text via VLM |
| Dyslexia-friendly Reader Mode | OpenDyslexic for Latin; **Odia-specific dyslexia rules (no letter-spacing, increased word-spacing and line-height)**; bionic reading; text simplification via LLM |
| Sign Language | ISL avatar (3D) for key phrases via phrase-book; ISLRTC Delhi partnership; research spike on full ISL translation |
| Accessibility Audit Tool | URL to WCAG report PDF + remediation suggestions; **Odia OCR via Surya** |

**Exit gate:** content in 12 languages (Odia + 11), live ISL avatar demo, audit tool in public beta, Odia dialect-robustness benchmark published.

---

### Phase 3 — Accessible Examinations *(Weeks 15-20)*

| Feature | Detail |
|---|---|
| Exam Engine | Question types (MCQ, match, numeric, essay) with accessibility metadata per item |
| Candidate profiles | PwD category to auto-applied accommodations (extra time %, scribe, audio, font) |
| Audio exams | TTS question playback, STT answer capture, voice navigation |
| Dyslexia mode | Font, spacing, chunked reading, text-to-speech per word |
| Scribe mode | Remote or in-person scribe with audit video (optional, consent-first) |
| Low-distraction proctoring | On-device anomaly detection (no always-on camera by default); human-in-the-loop review |
| Result accessibility | Accessible PDF certificates (tagged PDF/UA) |

**Exit gate:** mock exam with 50 PwD users across 3 disability categories; feedback drives v1.1.

---

### Phase 4 — Mobile & Kiosk *(Weeks 21-26)*

| Platform | Scope |
|---|---|
| Android/iOS SDK | Drop-in components; uses platform TalkBack/VoiceOver where available, our engine as fallback |
| Native app ("SaralAccess") | Document scan to read-aloud; photo to alt-text; fill-form assist |
| Physical Kiosk | Android tablet + external mic/speaker + optional Braille display; voice-first flow; NFC for profile load |
| Offline pack | Whisper-small + Piper models on-device; sync when online |

**Exit gate:** 5 kiosks deployed in pilot district offices; app shipped to Play Store / App Store.

---

### Phase 5 — Scale, Compliance, Govt Rollout *(Weeks 27-40)*

- **Reference deployment at OCAC, Bhubaneswar** as the flagship install; other states follow
- Multi-region deployment (at least 2 Indian regions for HA)
- DPDP Act Data Protection Officer workflows, consent manager, data-subject request portal
- ISO 27001 + CERT-In compliance audit
- STQC certification (govt software quality)
- Integration packs: DigiLocker, NAD, UDISE+, NIC eOffice, NTA exam formats, **Odisha-specific: Odisha One / e-Despatch / SAMS (Student Academic Management System)**
- National onboarding playbook + train-the-trainer program (Odisha first)
- Usage-based billing (per-institution) + free tier for schools below N students
- Public benchmarks dashboard (transparency: accuracy per language, latency, uptime; **Odia dialect accuracy broken out separately**)

---

### Phase 6 — Continuous *(ongoing)*

- Model retraining pipeline (new Indic voice data from opt-in contributions)
- Community plugin marketplace (verified by security review)
- Research track: low-resource tribal languages (Santhali, Bodo, Gondi), sign-language MT
- Red-team + bug bounty program

---

## 5. Team Composition (steady state)

| Track | People |
|---|---|
| Platform/Gateway | 2 BE eng |
| AI/ML (STT/TTS/MT) | 2 ML eng + 1 MLOps |
| Web/Widget | 2 FE eng |
| Mobile/Kiosk | 2 eng |
| Exam squad | 1 FE + 1 BE + 1 PM |
| Accessibility QA | 2 (including at least 1 PwD tester) |
| Security/Compliance | 1 |
| Design (inclusive) | 1 |
| DevOps/SRE | 1 |
| Product + Govt liaison | 1 PM |

Hackathon crew (SUBARNAREKHA) likely covers Phase 0 + a vertical slice of Phase 1 in 48 hours — that's the demo strategy. **One team member must be a native Odia speaker** to validate copy, tone, and demo pronunciation.

---

## 6. Risks & Mitigations (beyond the PDF's list)

| Risk | Mitigation |
|---|---|
| GPU cost spikes | Tiered models: edge Whisper-small first, escalate to large only when confidence low |
| Indic TTS quality (emotion, code-mix) | Fine-tune on institutional corpus; let users rate and collect consented samples |
| Govt procurement cycle slow | Parallel private-sector pilots (ed-tech, BFSI) to fund platform |
| Model hallucinations on simplification | Confidence scores + "original text" always one tap away; never simplify legal text without disclaimer |
| Accessibility overlays get a bad rap (industry criticism) | Ours is opt-in assistive layer, not a fix-for-broken-site band-aid; also ship the audit tool so sites fix root causes |
| On-prem govt deployments drift | Everything Terraform-modular + air-gapped model bundles |

---

## 7. Success Metrics (what we report to govt / public)

- **Reach:** number of institutions onboarded, monthly active PwD users
- **Quality:** WER per language (target < 15% for top 12 Indic), TTS MOS >= 4.0
- **Performance:** p95 TTS < 800ms, STT streaming < 300ms first-token
- **Accessibility:** 100% of our own surfaces WCAG 2.2 AA, 0 criticals in axe
- **Impact:** number of accessible exams conducted, self-reported user satisfaction by PwD category

---

## 8. Hackathon-demo Slice (smallest credible build)

If a working demo is needed in days, the smallest credible slice is:

1. **Web widget** (Preact, Shadow DOM) — read-aloud in **Odia**, font, contrast, Odia-aware dyslexia mode
2. **FastAPI service** — `/tts` (Indic-TTS for Odia) + `/stt` (IndicConformer for Odia) + `/translate` (IndicTrans2 via HF inference for Odia ↔ English)
3. **Admin dashboard** — one page: paste a URL, see axe audit + widget preview, Odia copy
4. **Demo site** — seeded as an **Odisha state-university admissions portal** with the widget live
5. **Pitch deck** tying back to the phased plan above and `docs/odia-language-strategy.md`

This proves the architecture, speaks directly to Odisha, and tells the phase-wise story judges want to hear.
