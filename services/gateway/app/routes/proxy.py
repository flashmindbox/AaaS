"""Routes that forward to upstream STT / TTS / admin-api services.

We register three APIRouters (one per upstream) so OpenAPI groups them
separately and per-route rate limits (Phase 1.2) can be applied
independently.
"""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request, Response

from app.auth import AuthContext, require_api_key
from app.config import Settings, get_settings
from app.proxy import forward


def _make_router(
    *,
    path_prefix: str,
    tag: str,
    upstream_attr: str,
) -> APIRouter:
    router = APIRouter(prefix=path_prefix, tags=[tag])

    @router.api_route(
        "/{path_suffix:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        include_in_schema=False,  # upstreams publish their own OpenAPI
    )
    async def _proxy(
        path_suffix: str,
        request: Request,
        auth: Annotated[AuthContext, Depends(require_api_key)],
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> Response:
        upstream_base: str = getattr(settings, upstream_attr)
        client: httpx.AsyncClient = request.app.state.http_client
        return await forward(
            client=client,
            upstream_base=upstream_base,
            request=request,
            auth=auth,
            path_suffix=path_suffix,
        )

    return router


tts_router = _make_router(
    path_prefix="/tts", tag="tts", upstream_attr="upstream_tts_url"
)
stt_router = _make_router(
    path_prefix="/stt", tag="stt", upstream_attr="upstream_stt_url"
)
translate_router = _make_router(
    path_prefix="/translate",
    tag="translate",
    upstream_attr="upstream_translate_url",
)
# Note: there is no admin_router anymore. /admin/api/* is served
# in-gateway by app.routes.admin_api; the /admin/ HTML dashboard is
# served statically by _mount_demo_assets. The earlier catch-all
# proxy would have shadowed the static mount with an API-key
# requirement, so removing it fixes /admin/ loads.
