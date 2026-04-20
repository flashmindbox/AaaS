# DPDP Act 2023 — Data-flow mapping for AaaS

**Scope:** every place personal data is collected, processed, stored, or
disclosed across the AaaS platform.
**Reference law:** Digital Personal Data Protection Act, 2023 (India).
**Owner:** Data Protection Officer (DPO) — role filled before first live
tenant.

The DPDP Act requires us, as a "Data Fiduciary" (and sometimes as a
"Data Processor" on behalf of tenant institutions), to document precisely
what personal data we handle, why, for how long, and how data principals
can exercise their rights. This document is the source of truth.

---

## 1. Data classification

| Class  | Definition                                                       | Examples in AaaS                                                      |
| ------ | ---------------------------------------------------------------- | --------------------------------------------------------------------- |
| **C0** | Non-personal / public                                            | Model weights, product docs, translated govt circulars                 |
| **C1** | Personal — identifies a person                                   | Email, staff name, tenant contact, IP address, OIDC `sub`             |
| **C2** | Sensitive personal — health, disability, biometric, minor status | Disability category, accommodation profile, scribe audio, face biometric |
| **C3** | Confidential platform                                            | API key hashes, model IP, pre-release exam papers                      |

Disability information is C2 — treat every accommodation record, STT audio
from a disabled candidate, and ISL video stream as C2 by default.

---

## 2. Data inventory (what we collect)

| # | Item                         | Class | Source               | Purpose                         | Legal basis (DPDP) |
| - | ---------------------------- | ----- | -------------------- | ------------------------------- | ------------------ |
| 1 | Tenant admin contact         | C1    | Institution signup   | Account management              | Contract           |
| 2 | End-user email / OIDC `sub`  | C1    | SSO login            | Auth + personalization          | Consent / contract |
| 3 | Browser / app usage events   | C1    | Telemetry            | Reliability, product analytics  | Legitimate use     |
| 4 | STT audio                    | C2    | Microphone upload    | Transcription                   | Consent            |
| 5 | TTS text                     | C1    | API request          | Synthesis                       | Contract           |
| 6 | OCR uploads                  | C1/C2 | User upload          | Document reading                | Consent            |
| 7 | Disability / accommodation   | C2    | Profile registration | Exam accommodations             | Consent            |
| 8 | Scribe recordings            | C2    | Exam session         | Dispute resolution              | Consent            |
| 9 | Kiosk camera frames          | C2    | Optional, off-by-default | Presence detection only       | Explicit consent   |
| 10| Audit log events             | C1    | System               | Security, regulatory            | Legal obligation   |
| 11| Consent records              | C1    | User action          | Proof of consent                | Legal obligation   |

Items 4, 6, 8, 9 are **strictly not retained** beyond the processing window
unless the user opts in to model-improvement contributions, which is a
separate, granular consent with a clear withdrawal flow.

---

## 3. Flow diagrams (textual)

### 3.1 Read-aloud flow (TTS)

```
End user -> Widget (browser)
         -> Gateway (TLS)
         -> TTS service
         -> [Piper/IndicTTS model]
         <- Audio bytes
         <- Audio streamed back
```

Data classes touched: C1 (text), C0 (audio output).
Retention: output audio cached by hash for 24 h for cost; text never stored.

### 3.2 Dictation flow (STT)

```
End user -> Widget (mic) -> Gateway (WSS)
                         -> STT service (streaming)
                         -> [Whisper/IndicWhisper]
                         <- Transcript tokens
                         <- Transcript finalized
```

Data classes: C2 (audio).
Retention: audio kept in memory only; zero-write unless the user explicitly
opts in to "help improve the model".

### 3.3 Exam with accommodations

```
Candidate -> Exam app -> Gateway
                     -> Exam engine
                     -> Accommodation profile lookup -> DB (C2)
                     -> Paper decryption (KEK from KMS)
                     -> Audio question stream (TTS, C1)
                     -> Answer capture (STT, C2 audio + C1 transcript)
                     -> Audit append (C1)
                     -> Scribe video (C2) to object store, access-logged
```

Retention: answers retained per exam-board policy (configurable per tenant);
scribe video retained 180 days default, deletable on request.

### 3.4 Cross-border / cross-zone

- **No personal data leaves India** without explicit DPDP-compliant
  cross-border approval. All prod infra in Indian regions.
- Model weights (C0/C3) may be mirrored to international CDN; never
  training data.

---

## 4. Retention matrix

| Data item                    | Default retention                  | Upper limit | Trigger to purge   |
| ---------------------------- | ---------------------------------- | ----------- | ------------------ |
| STT audio                    | None (in-memory)                   | 1 h         | Immediate on completion |
| STT audio (opted-in)         | 30 days                            | 90 days     | TTL + DSAR         |
| TTS audio cache              | 24 h                               | 7 d         | LRU / TTL          |
| OCR uploads                  | 24 h                               | 7 d         | Job completion + TTL |
| Accommodation profile        | Lifetime of enrolment              | 7 years post-enrolment | Account delete / DSAR |
| Exam answers                 | Per tenant config (typical 5 yr)   | 10 yr       | Tenant policy      |
| Scribe video                 | 180 d                              | 1 yr        | TTL                |
| Audit log                    | 1 y hot, 7 y cold                  | 7 y         | Legal hold allowed |
| Consent record               | Lifetime of processing + 7 y       | 7 y post    | Purge after retention |

Every retention rule above is enforced by an automated job — no manual
cleanup relied on.

---

## 5. Data-principal rights (DPDP §11-14)

We support all rights the Act grants. Each is a user-facing, self-serve flow:

| Right                  | How a user exercises it                       |
| ---------------------- | --------------------------------------------- |
| Access                 | "Download my data" in account settings         |
| Correction             | In-line edit for profile fields; support form |
| Erasure                | "Delete my account" — hard delete in 30 days  |
| Grievance redressal    | `grievance@aaas.platform` + ticket dashboard  |
| Nomination             | Nominee form in account settings              |
| Withdrawal of consent  | Per-purpose toggle in consent dashboard       |

SLA: 30 days to respond to any DSAR, mirroring DPDP expectation.

---

## 6. Consent UX

Every C1/C2 collection point surfaces a specific, purpose-bound notice:

- What is collected
- Why it is collected
- How long it is kept
- Who it is shared with (none, by default)
- Withdraw link

Consent is stored in `consent.records` with:

- Hashed subject id (not raw PII)
- Purpose code
- Policy version (immutable after publication)
- Timestamp + IP + UA as evidence

Withdrawn consent sets `withdrawn_at` and triggers deletion of derived data
within 72 h.

---

## 7. Breach response

| Step | Owner   | Target time |
| ---- | ------- | ----------- |
| Detect (alert fires)    | On-call SRE        | < 5 min      |
| Contain                 | On-call + security | < 30 min     |
| Assess scope            | Security + DPO     | < 2 h        |
| Notify Data Protection Board of India (if applicable) | DPO                | < 72 h       |
| Notify affected principals | Product           | per DPDP guidance |
| Post-mortem             | SRE                | within 7 d   |

A runbook lives in `/docs/security/breach-runbook.md` (to be authored in
Phase 1).

---

## 8. Processor relationships

When AaaS processes data on behalf of a tenant institution:

- AaaS is the **Data Processor**; the tenant is the **Data Fiduciary**.
- A Data Processing Agreement (DPA) is part of every tenant contract.
- The DPA specifies: purposes, duration, security measures, sub-processors,
  and audit rights.
- Sub-processors (e.g. cloud provider) are listed publicly and require
  48h notice of change.

---

## 9. Children and minors

- Users under 18 require verifiable parental consent for C2 collection
  beyond what is strictly necessary for an exam accommodation.
- Profiling and targeted advertising are prohibited for minors (we do not
  do advertising at all — simple blanket policy).
- Schools are "Data Fiduciaries" for student data; AaaS is their Processor.

---

## 10. Review cadence

- This document is reviewed at the start of every phase.
- Any code change that introduces a new data flow must update §2-4 before
  merge (enforced via PR template + CODEOWNERS).
- Annual third-party audit once the platform goes live.
