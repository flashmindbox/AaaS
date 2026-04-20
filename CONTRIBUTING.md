# Contributing to AaaS

Thanks for helping build an accessibility layer for public India. This
document describes the conventions contributors are expected to follow.

## Ground rules

1. **Accessibility is correctness.** A feature that is inaccessible is
   broken. `pnpm a11y` failing blocks the PR.
2. **Don't ship half-done.** Small, complete changes are better than large,
   partial ones.
3. **Don't add speculative abstractions.** If we need them, we will see them
   emerge from real code.
4. **Security and privacy are not optional.** Any new data flow requires
   updates to `docs/threat-model.md` and `docs/dpdp-data-flow.md`.

## Development setup

See `README.md` → Quickstart. The target is: a new contributor can clone,
install, and boot the stack in under 10 minutes on any OS.

## Code conventions

### TypeScript

- `strict: true`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`.
  These are set in `tsconfig.base.json` — do not loosen them per-package.
- Prefer explicit types for public APIs; let inference handle the rest.
- No `any` unless accompanied by a `// reason: ...` comment.

### React

- Function components only.
- Radix UI primitives preferred over hand-rolling accessibility.
- Every interactive control is built on top of `@aaas/ui` primitives or
  Radix — don't reinvent focus management, ARIA, or keyboard nav.

### Styling

- Use design tokens from `@aaas/ui`. Raw hex colors in app code are a
  review blocker.
- Never remove `:focus-visible` styles.
- Never suppress `prefers-reduced-motion`.

### Backend (future services)

- Python services: FastAPI, Pydantic v2, Ruff, Pytest. Line length 100.
  Google-style docstrings on public functions.
- Go services: idiomatic Go, golangci-lint. Context propagation always.
- All services ship OpenAPI and an SLO file.

## Commit message style

Conventional Commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci`,
`build`, `security`. Scope is the package or service name.

Examples:

```
feat(ui): add <SkipLink /> primitive
fix(a11y-test): correct wcag22aa tag typo
security(gateway): rotate default dev client secret
```

Breaking changes use `!` after the type/scope: `feat(ui)!: ...`.

## Branches + PRs

- Branch off `main`. Naming: `feat/...`, `fix/...`, `docs/...`.
- Keep PRs under ~500 lines of change where possible.
- Fill out the PR template (`.github/PULL_REQUEST_TEMPLATE.md`) fully.
- Request review from CODEOWNERS of touched paths.
- At least one approving review + all checks green before merge.
- Squash-merge by default; merge-commits are fine for large multi-file
  refactors.

## Accessibility expectations per PR

The PR template has this checklist. Every item is expected to be true
or explicitly justified:

- Passes `pnpm a11y`.
- Keyboard-only walkthrough done.
- Screen-reader verification done (name which AT).
- Color contrast ≥ 7:1 for new text.
- Target size ≥ 44x44 CSS px for new interactive elements.

## Testing expectations

- **Unit tests** for non-trivial logic.
- **Component tests** (React Testing Library + jest-axe) for every
  component that renders interactive UI.
- **Integration tests** for service endpoints when behavior crosses
  service boundaries.
- **Snapshot tests** are discouraged unless the output is genuinely stable.

## Security & privacy

- Run the PR template security section honestly. No new secrets ever
  committed (even in tests).
- If the PR adds or changes a personal-data flow, the PR description
  must explain:
  - What data class (C0-C3 per `docs/dpdp-data-flow.md`)
  - Legal basis under DPDP Act
  - Retention target
  - Consent surface if applicable
- CODEOWNERS auto-tags security on changes to sensitive paths.

## Adding a new package or app

1. Create directory under `apps/`, `services/`, or `packages/`.
2. Copy `package.json` shape from a sibling; use `@aaas/<name>` convention.
3. Extend `@aaas/config/tsconfig/<preset>` and `@aaas/config/eslint-preset`.
4. Add README, at least one test, and wire into `turbo.json` inputs if needed.
5. Update the relevant section README (`apps/README.md`, etc.).

## Code of Conduct

Be kind, direct, and technical. See `CODE_OF_CONDUCT.md`.

## Questions

Open a discussion on GitHub; for security concerns, use `SECURITY.md`
contact — do not open a public issue.
