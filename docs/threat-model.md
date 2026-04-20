# AaaS Threat Model (STRIDE)

**Scope:** the AaaS platform end-state (all services in `PLAN.md` §2).
**Frame:** STRIDE — Spoofing, Tampering, Repudiation, Information disclosure,
Denial of service, Elevation of privilege.
**Owner:** Security workstream. Reviewed at the start of every phase and
any time a new data flow is introduced.

---

## 0. Assumptions

- All traffic between clients and gateway is TLS 1.3; internal traffic runs
  on mTLS inside the cluster.
- Secrets are in a KMS (AWS KMS / GCP KMS / Vault) — never in env files in
  production.
- Observability is on for every service (OTel traces, structured logs,
  metrics).
- DPDP Act 2023 governs all personal data — see `dpdp-data-flow.md`.

---

## 1. Assets and trust zones

| Asset                                | Owner               | Sensitivity  |
| ------------------------------------ | ------------------- | ------------ |
| End-user audio (STT input)           | End user            | High (PII)   |
| Synthesized audio                    | Platform            | Low          |
| Uploaded documents (OCR)             | End user / tenant   | Variable     |
| Exam papers (pre-release)            | Tenant (exam board) | Critical     |
| Candidate accommodation records      | End user            | High (sPII)  |
| API keys / OIDC client secrets       | Platform / tenant   | Critical     |
| Model weights                        | Platform            | Medium (IP)  |
| Audit logs                           | Platform            | High         |
| Consent records                      | End user            | High         |

Trust zones:

```
  [Internet]
      |  TLS
  [Edge CDN / WAF]
      |
  [API Gateway]        <-- zone boundary
      |  mTLS
  [Internal services]  <-- zone boundary
      |
  [Data plane: DB, Redis, S3, Keycloak]
      |
  [Model plane: Triton / vLLM GPU nodes]
```

---

## 2. STRIDE per component

### 2.1 API Gateway

| STRIDE | Threat                                                       | Mitigation                                                                                           |
| ------ | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| S      | Attacker forges JWT / API key                                | RS256 JWTs from Keycloak; API keys stored as sha256 + prefix lookup; mTLS for service-to-service     |
| T      | Request/response tampering                                   | TLS everywhere; HMAC on webhook bodies; body-size and content-type enforcement at edge               |
| R      | Tenant disputes a destructive action                         | Append-only `audit.events` table; no UPDATE/DELETE via DB trigger; audit shipped to immutable store  |
| I      | PII leaks in error messages / logs                           | Central error shaper strips bodies; structured logger redacts known sensitive fields                 |
| D      | Burst traffic / request amplification                        | Per-tenant rate limits; 429 with `Retry-After`; circuit-breakers to slow/broken backends; WAF        |
| E      | Cross-tenant data access via IDOR                            | Every request carries `tenant_id`; all queries filter by it; integration tests assert cross-tenant 403 |

### 2.2 STT service

| STRIDE | Threat                                   | Mitigation                                                                                          |
| ------ | ---------------------------------------- | --------------------------------------------------------------------------------------------------- |
| S      | Unauthenticated transcription requests   | Only reachable via gateway; mTLS client cert required                                               |
| T      | Injected adversarial audio               | Content-type allowlist; max-duration cap; MIME sniff; reject non-audio                              |
| R      | Provider denies abuse                    | Request ID propagated; audit log has actor + audio hash (never raw audio)                          |
| I      | Audio retained in logs or model memory   | Audio deleted from S3 after transcription (< 1 h); Whisper is stateless; no audio in logs          |
| D      | GPU exhaustion by giant audio            | Per-request size/duration caps; queue with priority per plan; admission control on GPU pool        |
| E      | RCE via model loader                     | Run under unprivileged UID; seccomp profile; read-only filesystem; no shell; weights from signed registry |

### 2.3 TTS service

| STRIDE | Threat                                       | Mitigation                                                                 |
| ------ | -------------------------------------------- | -------------------------------------------------------------------------- |
| S      | Replay of costly requests                    | Caching keyed by (text-hash, voice, lang); rate limits per tenant         |
| T      | SSML injection to fetch external resources   | SSML parser forbids external refs; strict subset allowlist                 |
| R      | Plagiarised voice ("voice deepfake")         | Only licensed voices; voice ID in audit; watermark audio (inaudible)       |
| I      | Text leaks via TTS output cache shared across tenants | Cache key includes `tenant_id`; per-tenant namespaces                      |
| D      | Huge text blocks                             | Character caps per request; chunked synthesis with client-side stitching   |
| E      | Arbitrary code in custom voices              | Voices are data, not code; no plugin loading from user input               |

### 2.4 Translation service

| STRIDE | Threat                                      | Mitigation                                                                |
| ------ | ------------------------------------------- | ------------------------------------------------------------------------- |
| S      | Cross-tenant glossary access                | Glossaries keyed by tenant; cache namespaced                              |
| T      | Prompt injection via input text (for LLM-backed modes) | Segment-level translation; no tool-use; output filter against tag injection |
| R      | Model hallucination mis-translation causes harm       | Confidence score returned; UI must show original alongside translation     |
| I      | Content in logs                             | Log only hashes + language pair + length; no raw text                     |
| D      | Huge documents                              | Chunked pipeline; per-tenant concurrency caps                             |
| E      | n/a                                         | n/a                                                                       |

### 2.5 Screen Reader service (server-side VLM for alt-text)

| STRIDE | Threat                                                  | Mitigation                                                          |
| ------ | ------------------------------------------------------- | ------------------------------------------------------------------- |
| S      | Spoofed image URLs to exfil internal resources (SSRF)   | URL allowlist per tenant; resolve and block private ranges; timeout |
| T      | Image content injection (XSS via alt-text output)       | Output is plain text; HTML-escape; no rich content                  |
| R      | False/harmful alt text cited later                      | Responses tagged "AI-generated"; user can edit; store diff trail    |
| I      | Uploaded image persisted beyond need                    | In-memory only unless user consents to persistence                  |
| D      | Large images                                            | Size / pixel limits                                                 |
| E      | Model weight tampering                                  | Signed weights, checksum on load                                    |

### 2.6 Exam Engine

| STRIDE | Threat                                                      | Mitigation                                                                                     |
| ------ | ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| S      | Candidate impersonation                                     | Keycloak auth + optional biometric check at start (opt-in, DPDP-compliant)                    |
| T      | Answer tampering in transit                                 | Signed client submissions; server-side re-timing; replay-resistant nonces                     |
| R      | Candidate disputes their answers                            | Every answer event appended to immutable audit log with hash-chain                            |
| I      | Pre-release paper leak                                      | Papers encrypted at rest with per-exam KEK; decrypted only in enclave/at start-of-exam window |
| D      | Exam platform DoS at test start                             | Pre-signed sessions; scheduled warm-up; queueing with back-off                                |
| E      | Elevated access to other candidates' papers                 | Strict RLS — candidate can only read own attempt; invigilator role separate                   |

### 2.7 Admin API / Dashboard

| STRIDE | Threat                                 | Mitigation                                                         |
| ------ | -------------------------------------- | ------------------------------------------------------------------ |
| S      | Session hijack                         | SameSite=Lax cookies; HttpOnly; Secure; short TTL + refresh        |
| T      | CSRF                                   | Double-submit cookie or OAuth-flow tokens                          |
| R      | Tenant disputes a config change        | Every admin mutation in audit log with actor + diff                |
| I      | Sensitive metrics exposed publicly     | Auth-required on all admin routes; metrics scoped to tenant        |
| D      | Scrape protection                      | Per-IP + per-token throttling                                      |
| E      | Privilege escalation via role editor   | Role changes require MFA + second-admin approval for sensitive grants |

### 2.8 Web Widget (in-browser)

| STRIDE | Threat                                  | Mitigation                                                    |
| ------ | --------------------------------------- | ------------------------------------------------------------- |
| S      | Widget impersonation on hostile site    | Widget verifies tenant against licensed domain list            |
| T      | Host page injects into widget UI        | Shadow DOM isolation; host CSS cannot reach in                 |
| R      | User disputes action taken in widget    | Widget logs to gateway with session id                         |
| I      | Widget sends data to unintended origin  | All calls go to configured gateway; no third-party beacons     |
| D      | Widget script blocks page               | Async loader; < 30 KB gzip budget; initializes on idle         |
| E      | XSS in widget injected into host        | CSP-compatible; no inline scripts; no `innerHTML` with user data |

### 2.9 Mobile SDK / SaralAccess app

| STRIDE | Threat                                          | Mitigation                                                                 |
| ------ | ----------------------------------------------- | -------------------------------------------------------------------------- |
| S      | Stolen device session                           | OS-backed keystore; biometric re-auth; session binding to device attest    |
| T      | Tampered APK                                    | Play Store + Play Integrity API; server re-verifies                        |
| R      | n/a                                             | n/a                                                                        |
| I      | PII cached on disk                              | No persistent storage for audio; EncryptedSharedPreferences where required |
| D      | Network starvation forces online-only           | Offline pack for core TTS/STT; degraded-mode UX                            |
| E      | Malicious app impersonating SaralAccess         | Code-signing; app-links with verified domain                               |

### 2.10 Kiosk

| STRIDE | Threat                                   | Mitigation                                                           |
| ------ | ---------------------------------------- | -------------------------------------------------------------------- |
| S      | Someone installs a hostile app           | Android managed kiosk mode; Device Policy Controller                 |
| T      | USB-based side-load                      | USB-host disabled; hardware switch; signed OTA only                  |
| R      | Session carry-over between citizens      | Session cleared + mic audio purged on timeout or explicit "done"     |
| I      | Mic picks up next-in-line conversation   | Push-to-talk default; directional mic; VAD cutoff                    |
| D      | Vandalism / cord pull                    | Physical enclosure; watchdog restart                                 |
| E      | Root / factory reset by attacker         | Secure boot + verified boot; factory reset requires admin cert       |

---

## 3. Cross-cutting controls

1. **Secrets management** — every secret in KMS; never in env files in prod;
   rotation on a 90-day cadence; access logged.
2. **Supply chain** — SBOMs generated on every main push; Dependabot + Grype;
   signed container images (cosign); reproducible builds where feasible.
3. **Dependency pinning** — `packageManager` field pinned; lockfiles required
   in CI; `pnpm install --frozen-lockfile`.
4. **Least privilege** — service accounts per service; RLS in Postgres for
   multi-tenant tables; S3 bucket policies scoped by tenant prefix.
5. **Logging hygiene** — structured logs only; PII allowlist, not blocklist;
   log scrubber at the edge.
6. **Backups & recovery** — daily encrypted backups; restore-drill quarterly;
   RPO 1 h, RTO 4 h for tier-1 services.
7. **Red team** — internal red-team every major release; external bug bounty
   once platform reaches public beta.

---

## 4. Residual risks accepted for Phase 0

- No real security review of Keycloak realm export (will be re-done before
  any tenant onboards).
- Docker Compose dev uses hardcoded passwords — only for `localhost`.
- No mTLS inside dev environment (adds cost; re-introduced in staging/prod
  via service mesh).

All residuals are tracked with owners and target-resolution phases in the
security backlog. See `/docs/security/` once that directory exists.
