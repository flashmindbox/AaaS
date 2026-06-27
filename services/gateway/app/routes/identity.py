"""`/whoami` — a cheap way for clients to verify their API key works.

The widget calls this once at mount to surface a helpful error if the
tenant operator configured a wrong key. It also lets us smoke-test auth
end-to-end without needing a full STT/TTS pipeline running.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import AuthContext, require_api_key

router = APIRouter(tags=["identity"])


class WhoAmIResponse(BaseModel):
    tenant_slug: str
    tenant_display_name: str
    tenant_region: str | None
    scopes: list[str]


@router.get("/whoami", response_model=WhoAmIResponse)
async def whoami(
    auth: Annotated[AuthContext, Depends(require_api_key)],
) -> WhoAmIResponse:
    return WhoAmIResponse(
        tenant_slug=auth.tenant.slug,
        tenant_display_name=auth.tenant.display_name,
        tenant_region=auth.tenant.region,
        scopes=list(auth.api_key.scopes),
    )
