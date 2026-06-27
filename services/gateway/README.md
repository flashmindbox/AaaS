# @aaas/gateway

Single public entry point for the AaaS Phase 1 services. Everything a client
(widget, dashboard, SDK) hits goes through here; nothing downstream is
exposed to the public internet.

## Responsibilities

- **Authentication** — OIDC via Keycloak (staff / admins) and static API
  keys (machine-to-machine, per-tenant).
- **Tenant resolution** — resolve the caller's tenant and attach it to the
  request context so downstream services never have to re-check.
- **Rate limiting** — token-bucket in Redis, defaults configurable per
  tenant.
- **Request logging** — structured audit log (JSON to stdout, ingested by
  Loki in real deployments).
- **Routing** — proxy `/tts/*`, `/stt/*`, and `/admin/*` to the respective
  upstream services.

## Why FastAPI (not Go / not Kong)

`PLAN.md §3` originally listed Kong with a custom auth plugin. For Phase 1
hackathon speed we ship a FastAPI gateway instead:

- One fewer runtime in the dev stack.
- Same Python ecosystem as the STT/TTS services, so engineers context-
  switch less.
- Phase 1 MVP traffic doesn't need Go / Kong latency floors.
- Swap path: Phase 3 compliance review can front this with Kong (or Envoy)
  without changing upstream services — the gateway's responsibilities move
  up-stack, not sideways.

## Local dev

Prereqs: Python 3.12 or newer (3.14 works), the infra stack running
(`pnpm infra:up` from the repo root).

```bash
cd services/gateway
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash
# source .venv/bin/activate      # macOS / Linux
pip install -e '.[dev]'
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Then:

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/version
open http://localhost:8000/docs    # OpenAPI / Swagger UI
```

## Testing

```bash
pytest                    # whole suite
pytest -k health          # just the liveness tests
pytest --cov=app          # coverage
```

## Lint & typecheck

```bash
ruff check .
ruff format .
mypy app
```

## What is NOT here yet (tracked)

These land in follow-up tasks on the same Phase 1 branch:

- OIDC JWT validation middleware (Keycloak JWKS).
- API-key validation middleware (Postgres lookup, Redis cache).
- Tenant-scoped rate limits (Redis token-bucket).
- Upstream proxy routes to TTS / STT / admin-api.
- OpenTelemetry tracing export.
- Structured audit-log sink.
