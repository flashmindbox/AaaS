"""Audit-log middleware.

Every HTTP request that hits the gateway is recorded to an in-memory
ring buffer so the admin dashboard can show a rolling 24 h view of
traffic without needing Postgres. Strictly demo-grade — the ring
buffer is process-local, bounded to ``MAX_EVENTS``, and doesn't
persist across restarts. That's fine for the hackathon pitch; the
dashboard's job is to *show the pattern*, not to be a billing ledger.

Structure (kept small — each event is ~200 bytes):

    AuditEvent(
        ts="2026-04-21T14:03:22Z",
        method="POST",
        path="/tts/synthesise",
        status=200,
        latency_ms=142,
        tenant_slug="utkal-university" | None,
    )

To read them from a route handler:

    events = request.app.state.audit_log.recent(minutes=60)
"""

from __future__ import annotations

import collections
import dataclasses
import time
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

MAX_EVENTS = 5_000


@dataclasses.dataclass(slots=True, frozen=True)
class AuditEvent:
    ts: datetime
    method: str
    path: str
    status: int
    latency_ms: int
    tenant_slug: str | None


class AuditLog:
    """Thread-unsafe ring buffer — FastAPI is single-loop, fine for demos."""

    def __init__(self, maxlen: int = MAX_EVENTS):
        self._buf: collections.deque[AuditEvent] = collections.deque(maxlen=maxlen)

    def record(self, event: AuditEvent) -> None:
        self._buf.append(event)

    def recent(self, *, minutes: int = 60) -> list[AuditEvent]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return [e for e in self._buf if e.ts >= cutoff]

    def all(self) -> Iterator[AuditEvent]:
        return iter(self._buf)

    def clear(self) -> None:
        self._buf.clear()


class AuditMiddleware(BaseHTTPMiddleware):
    """Record every response to ``request.app.state.audit_log``.

    Tenant slug comes from ``request.state.auth`` if an auth dependency
    already attached one; otherwise None (e.g. /healthz).
    """

    async def dispatch(
        self, request: Request, call_next: Callable[..., object]
    ) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        tenant_slug: str | None = None
        auth = getattr(request.state, "auth", None)
        if auth is not None:
            tenant_slug = auth.tenant.slug

        log: AuditLog | None = getattr(request.app.state, "audit_log", None)
        if log is not None:
            log.record(
                AuditEvent(
                    ts=datetime.now(timezone.utc),
                    method=request.method,
                    path=request.url.path,
                    status=response.status_code,
                    latency_ms=elapsed_ms,
                    tenant_slug=tenant_slug,
                )
            )
        return response
