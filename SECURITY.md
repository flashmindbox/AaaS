# Security policy

## Supported versions

AaaS is pre-release (Phase 0). Only `main` is supported; there are no
released versions yet.

## Reporting a vulnerability

**Do not file a public GitHub issue for security reports.**

Email `security@aaas.platform` with:

1. A description of the issue and where it is.
2. Steps to reproduce — the smaller the better.
3. Impact assessment (what an attacker could do).
4. Your contact info if you want credit.

Expected response times:

| Step              | Target  |
| ----------------- | ------- |
| Acknowledgement   | < 48 h  |
| Triage            | < 7 d   |
| Fix + coordinated disclosure | < 90 d, sooner for critical |

## Out of scope

- Attacks requiring physical access to a user's device.
- Self-XSS without a practical vector.
- Denial of service against the dev environment (`docker compose`).
- Issues in third-party dependencies already tracked in our SBOM
  workflow — report those upstream.

## Safe harbor

Good-faith security research following this policy is authorized. We
will not pursue legal action against researchers who:

- Make a good-faith effort to avoid privacy violations, data loss, or
  service disruption.
- Give us reasonable time to investigate and fix the issue before
  public disclosure.

## Related documents

- `docs/threat-model.md` — STRIDE threat model
- `docs/dpdp-data-flow.md` — DPDP Act data-flow mapping
