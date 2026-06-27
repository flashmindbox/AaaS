"""Upstream HTTP proxy helpers.

The gateway forwards `/tts/*`, `/stt/*`, and `/admin/*` to the
corresponding upstream services. On the way out:

- API-key headers are *stripped* (upstreams never see them — they trust
  tenant context from `X-Tenant-*` headers signed by the gateway).
- `X-Tenant-Id`, `X-Tenant-Slug`, `X-Tenant-Region` are appended so
  downstream services can route or audit per-tenant without re-reading
  Postgres.
- Hop-by-hop headers (``Connection``, ``Transfer-Encoding`` etc.) are
  dropped per RFC 7230 §6.1.

On the way back, the upstream status code, body, and allow-listed
headers are mirrored to the caller. Connection errors map to 502;
read/connect timeouts to 504.
"""

from __future__ import annotations

from collections.abc import Iterable

import httpx
from fastapi import HTTPException, Request, Response, status
from starlette.background import BackgroundTask

from app.auth import AuthContext

# Headers that must not be forwarded per RFC 7230.
_HOP_BY_HOP: frozenset[str] = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)

# Inbound headers we strip before forwarding (secrets / gateway-only).
_STRIP_INBOUND: frozenset[str] = frozenset(
    {
        "x-api-key",
        "authorization",
        "host",
        "content-length",  # httpx recomputes
    }
)

# Outbound headers we do NOT mirror from upstream (already set by FastAPI).
_STRIP_OUTBOUND: frozenset[str] = frozenset(
    {
        "content-length",
        "content-encoding",  # httpx already decoded
    }
)


def _forwardable_request_headers(
    src: Iterable[tuple[str, str]],
) -> list[tuple[str, str]]:
    return [
        (k, v)
        for k, v in src
        if k.lower() not in _HOP_BY_HOP and k.lower() not in _STRIP_INBOUND
    ]


def _forwardable_response_headers(
    src: Iterable[tuple[str, str]],
) -> list[tuple[str, str]]:
    return [
        (k, v)
        for k, v in src
        if k.lower() not in _HOP_BY_HOP and k.lower() not in _STRIP_OUTBOUND
    ]


def _tenant_headers(auth: AuthContext) -> dict[str, str]:
    return {
        "X-Tenant-Id": str(auth.tenant.id),
        "X-Tenant-Slug": auth.tenant.slug,
        "X-Tenant-Region": auth.tenant.region or "",
    }


async def forward(
    *,
    client: httpx.AsyncClient,
    upstream_base: str,
    request: Request,
    auth: AuthContext,
    path_suffix: str,
) -> Response:
    """Issue the upstream call and return a FastAPI response mirroring it."""
    url = f"{upstream_base.rstrip('/')}/{path_suffix.lstrip('/')}"
    headers = _forwardable_request_headers(request.headers.items())
    headers.extend(_tenant_headers(auth).items())

    try:
        body = await request.body()
        upstream_response = await client.request(
            method=request.method,
            url=url,
            content=body,
            headers=headers,
            params=request.query_params,
        )
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream unreachable: {exc!s}",
        ) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Upstream timed out",
        ) from exc

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=dict(
            _forwardable_response_headers(upstream_response.headers.items())
        ),
        media_type=upstream_response.headers.get("content-type"),
        background=BackgroundTask(upstream_response.aclose),
    )
