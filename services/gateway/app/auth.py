"""FastAPI auth dependencies.

Two authentication paths:

- **API key** (`X-API-Key` header) — machine-to-machine, per-tenant.
  This is what the widget and SDK use. Implemented in this module.
- **OIDC JWT** (`Authorization: Bearer ...`) — staff/admin users via
  Keycloak. Lands in Phase 1.2 (`app/auth_oidc.py`).

Routes opt in by declaring `Depends(require_api_key)`. Health routes
deliberately don't, so liveness probes stay cheap.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.tenants import ApiKey, Tenant, TenantRepository


@dataclass(frozen=True, slots=True)
class AuthContext:
    """Attached to `request.state.auth` by :func:`require_api_key`."""

    tenant: Tenant
    api_key: ApiKey


def _get_repository(request: Request) -> TenantRepository:
    """Pulled off app.state so tests can override it."""
    repo: TenantRepository | None = getattr(
        request.app.state, "tenant_repository", None
    )
    if repo is None:
        raise RuntimeError(
            "tenant_repository not configured on app.state; see app.main"
        )
    return repo


async def require_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    repo: Annotated[TenantRepository, Depends(_get_repository)] = None,  # type: ignore[assignment]
) -> AuthContext:
    """Validate `X-API-Key` header and attach tenant context to the request.

    Returns the :class:`AuthContext` so route handlers can read
    `auth.tenant` / `auth.api_key` directly via their own
    `auth: Annotated[AuthContext, Depends(require_api_key)]` parameter.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    match = await repo.find_tenant_by_api_key(x_api_key)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    tenant, api_key = match
    auth = AuthContext(tenant=tenant, api_key=api_key)
    request.state.auth = auth
    return auth
