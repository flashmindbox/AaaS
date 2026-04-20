# AaaS — Accessibility as a Service

> A centralized, cloud-based accessibility infrastructure for Indian public
> institutions. Plug-and-play APIs for speech, translation, screen-reader
> support, accessible examinations, and more — so no citizen is shut out of
> their own government.

**Team:** SUBARNAREKHA · **License:** Apache-2.0 · **Status:** Phase 0 — foundations

## Why this exists

Every Indian university, exam board, and government portal today builds its
own (usually poor, usually absent) accessibility. That duplication leaves
millions of citizens with disabilities, with learning differences, or who
speak languages other than English, unable to use their own government's
digital services. AaaS builds that layer **once, centrally** so every
institution can switch it on in a day.

Read more:

- [`WHAT_WE_ARE_BUILDING.md`](./WHAT_WE_ARE_BUILDING.md) — plain-English vision
- [`PLAN.md`](./PLAN.md) — technical blueprint and phase-wise roadmap
- [`docs/`](./docs) — threat model, DPDP data-flow mapping, WCAG checklist

## Quickstart (10-minute setup)

```bash
# 1. Prerequisites (one-time, global)
#    Node 20+, pnpm 10+, Docker Desktop, Git.
#    Optional for services/: Python 3.11+, Go 1.22+.
node -v && pnpm -v && docker -v

# 2. Install dependencies
pnpm install

# 3. Boot the local dev stack (Postgres, Redis, MinIO, Keycloak, Jaeger, MailHog)
pnpm infra:up

# 4. Build everything and run tests
pnpm build
pnpm test
pnpm a11y    # WCAG 2.2 AA harness self-test
```

| Dashboard       | URL                    | Credentials           |
| --------------- | ---------------------- | --------------------- |
| Keycloak        | http://localhost:8080  | admin / admin         |
| Keycloak user   | same                   | dev / dev (realm: aaas) |
| MinIO console   | http://localhost:9001  | aaas-dev / aaas-dev-secret |
| MailHog         | http://localhost:8025  | —                     |
| Jaeger          | http://localhost:16686 | —                     |
| Postgres        | localhost:5432         | aaas / change-me-in-dev (db: aaas) |

Shut down with `pnpm infra:down`; wipe volumes with `pnpm infra:reset`.

## Repo layout

```
aaas/
├── apps/          # end-user apps (widget, dashboard, exam, mobile, kiosk)
├── services/      # backend microservices (gateway, stt, tts, mt, exam ...)
├── packages/      # shared libraries
│   ├── config/       # @aaas/config — eslint, tsconfig, prettier presets
│   ├── ui/           # @aaas/ui — accessible design system (AAA contrast)
│   └── a11y-test/    # @aaas/a11y-test — axe + Playwright WCAG harness
├── infra/         # docker-compose dev stack, Keycloak realm, Postgres init
├── docs/          # threat model, DPDP, WCAG checklist
├── .github/       # workflows, CODEOWNERS, PR/issue templates
└── (root configs) # pnpm-workspace, turbo, tsconfig.base, eslint, prettier
```

## Common commands

| Command                     | What it does                                         |
| --------------------------- | ---------------------------------------------------- |
| `pnpm dev`                  | Watch-mode dev across all workspaces                 |
| `pnpm build`                | Build all packages (Turbo runs in parallel, cached)  |
| `pnpm lint`                 | ESLint + jsx-a11y strict rules                       |
| `pnpm typecheck`            | Strict TypeScript across all packages                |
| `pnpm test`                 | Vitest unit tests (incl. axe + contrast regressions) |
| `pnpm a11y`                 | WCAG 2.2 AA audit harness                            |
| `pnpm format`               | Prettier --write                                     |
| `pnpm format:check`         | CI-safe format check                                 |
| `pnpm infra:up / down / reset` | Dev stack lifecycle                               |

Turbo is configured with proper input/output tracking, so reruns that
touch nothing hit cache in milliseconds.

## Quality gates

CI (GitHub Actions) enforces the following on every PR:

1. **Install** — `pnpm install --frozen-lockfile`
2. **Lint + format** — ESLint with `jsx-a11y/strict`, Prettier check
3. **Typecheck** — strict TS
4. **Unit tests** — including `jest-axe` for every component and
   color-contrast regression tests for the design system
5. **A11y audit** — `pnpm a11y` (axe-core via Playwright)
6. **Build** — full monorepo build
7. **SBOM + vuln scan** — CycloneDX SBOM via Syft; Grype on high-severity;
   SARIF uploaded to GitHub Code Scanning

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). The short version:

- Accessibility is a correctness concern, not a nice-to-have. PRs that
  regress `pnpm a11y` are blocked.
- Keep scope tight — smaller PRs merge faster.
- Security and privacy changes need a threat-model / DPDP review before
  merge (see `docs/` and `CODEOWNERS`).

## Security

Responsible disclosure: see [`SECURITY.md`](./SECURITY.md).
Threat model: [`docs/threat-model.md`](./docs/threat-model.md).
Data protection: [`docs/dpdp-data-flow.md`](./docs/dpdp-data-flow.md).

## License

Apache-2.0. See [`LICENSE`](./LICENSE).
