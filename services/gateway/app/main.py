"""FastAPI application factory.

The factory pattern lets tests spin up a fresh app per test-module with
different overrides, and lets prod/dev wire different middleware stacks
(e.g. OTel exporter only in prod).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

import httpx
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import Settings, get_settings
from app.middleware.audit import AuditLog, AuditMiddleware
from app.routes import admin_api, health, identity, proxy
from app.tenants import InMemoryTenantRepository, Tenant, TenantRepository

logger = structlog.get_logger(__name__)


def _configure_logging(level: str) -> None:
    """Wire structlog so every log line is JSON with request context."""
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level)
        ),
    )


def _seed_dev_repository() -> InMemoryTenantRepository:
    """Seed three tenants so the admin dashboard has data to show.

    The keys below are deliberately public in source control — they only
    unlock the local dev tenants, not production data. Postgres-backed
    repositories land in Phase 1.2.

    The "utkal-university" slug is treated as the operator tenant
    (sees all tenants in admin endpoints); the other two are regular
    "customer" tenants.
    """
    repo = InMemoryTenantRepository()
    utkal = Tenant(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        slug="utkal-university",
        display_name="Utkal University",
        category="university",
        region="IN-OD",
    )
    repo.add(utkal, raw_key="aaas_live_" + "0" * 32, name="operator-seed")

    jajpur = Tenant(
        id=UUID("00000000-0000-0000-0000-000000000002"),
        slug="jajpur-collectorate",
        display_name="Jajpur Collectorate",
        category="government",
        region="IN-OD",
    )
    repo.add(jajpur, raw_key="aaas_live_" + "1" * 32, name="jajpur-seed")

    bse = Tenant(
        id=UUID("00000000-0000-0000-0000-000000000003"),
        slug="bse-odisha",
        display_name="Board of Secondary Education, Odisha",
        category="exam-board",
        region="IN-OD",
    )
    repo.add(bse, raw_key="aaas_live_" + "2" * 32, name="bse-seed")

    ssepd = Tenant(
        id=UUID("00000000-0000-0000-0000-000000000004"),
        slug="ssepd-odisha",
        display_name="SSEPD Department, Odisha",
        category="government",
        region="IN-OD",
    )
    repo.add(ssepd, raw_key="aaas_live_" + "3" * 32, name="ssepd-seed")

    aiims = Tenant(
        id=UUID("00000000-0000-0000-0000-000000000005"),
        slug="aiims-bhubaneswar",
        display_name="AIIMS Bhubaneswar",
        category="healthcare",
        region="IN-OD",
    )
    repo.add(aiims, raw_key="aaas_live_" + "4" * 32, name="aiims-seed")
    return repo


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown — DB pools and Redis clients live here (Phase 1.2)."""
    settings: Settings = app.state.settings
    # Only seed a default if the caller didn't inject one (tests do).
    if not hasattr(app.state, "tenant_repository"):
        app.state.tenant_repository = _seed_dev_repository()
    # In-memory audit log feeding the admin usage endpoint. Bounded
    # ring buffer — see app.middleware.audit.
    app.state.audit_log = AuditLog()
    # Per-tenant WCAG scan results are kept here by admin_api.
    app.state.wcag_results = {}
    # Single shared httpx client for all upstream calls. Connection pool
    # is cheap but non-trivial to build, so we re-use it across requests.
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=3.0, read=30.0, write=10.0, pool=3.0),
        follow_redirects=False,
    )
    logger.info(
        "gateway.start",
        version=__version__,
        env=settings.aaas_env,
        port=settings.gateway_port,
    )
    try:
        yield
    finally:
        await app.state.http_client.aclose()
        logger.info("gateway.stop")


def create_app(
    settings: Settings | None = None,
    tenant_repository: TenantRepository | None = None,
) -> FastAPI:
    """Build the FastAPI app.

    Pass `settings` in tests to override env. Pass `tenant_repository` to
    swap in an in-memory / faked repo so tests don't need Postgres.
    """
    settings = settings or get_settings()
    _configure_logging(settings.log_level)

    app = FastAPI(
        title="AaaS Gateway",
        version=__version__,
        description=(
            "Single public entry point for Phase 1 services (STT, TTS, "
            "admin-api). Handles OIDC auth, API-key validation, tenant "
            "resolution, per-tenant rate limits, and request logging."
        ),
        lifespan=_lifespan,
    )
    app.state.settings = settings
    if tenant_repository is not None:
        app.state.tenant_repository = tenant_repository
    # CORS: the browser extension injects widget.js into arbitrary pages,
    # so fetches to /tts, /stt, /translate arrive from origins the gateway
    # has never seen. Allow any origin but keep the allowed methods and
    # headers tight — we don't accept cookies, only the X-API-Key header,
    # so allow_credentials stays False (which also keeps "*" legal).
    #
    # allow_private_network: the widget runs on public https sites but calls
    # this gateway on loopback (127.0.0.1). Chrome's Private Network Access
    # sends the preflight with Access-Control-Request-Private-Network: true
    # and blocks the request unless the server echoes back
    # Access-Control-Allow-Private-Network: true. Without this, the widget
    # works on the same-origin demo but is blocked on real third-party sites.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key", "Authorization"],
        allow_private_network=True,
        max_age=600,
    )
    app.add_middleware(AuditMiddleware)
    app.include_router(health.router)
    app.include_router(identity.router)
    # /admin/api/* is served in-gateway by admin_api.router. The admin
    # dashboard HTML lives under /admin/ via _mount_demo_assets. There is
    # no admin upstream service, so the old proxy.admin_router is gone —
    # leaving it registered would shadow the static /admin/ mount with a
    # catch-all that requires an API key for HTML loads.
    app.include_router(admin_api.router)
    app.include_router(proxy.tts_router)
    app.include_router(proxy.stt_router)
    app.include_router(proxy.translate_router)
    _mount_demo_assets(app)
    return app


def _mount_demo_assets(app: FastAPI) -> None:
    """Serve the widget + demo sites from the same origin as the gateway.

    This sidesteps CORS for the Phase A demo — judge opens the gateway
    URL, the page loads widget.js from the same origin, and the widget
    POSTs to /tts/synthesise on that same origin.

    Paths are relative to the gateway's repo location. If the folders
    aren't present (e.g. a prod deploy that doesn't ship demo assets),
    mounts are silently skipped.
    """
    # Three deploy shapes to cover:
    #   dev          : services/gateway/app/main.py -> apps/ at parents[3]
    #   docker       : /app/app/main.py with apps/ COPIEd to /app/apps
    #                  (which is parent.parent of main.py, aka parents[1])
    #   PyInstaller  : assets live under sys._MEIPASS/apps/... — try first.
    # Rather than branch on deploy shape, walk every ancestor of main.py
    # plus cwd and just ask "does this directory have an apps/ child?".
    import sys as _sys

    candidates: list[Path] = []
    meipass = getattr(_sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass))
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidates.append(parent)
    candidates.append(Path.cwd())

    widget_file: Path | None = None
    demo_dir: Path | None = None
    admin_dir: Path | None = None
    for root in candidates:
        w = root / "apps" / "widget" / "dist" / "widget.js"
        d = root / "apps" / "demo-sites"
        a = root / "apps" / "admin"
        if widget_file is None and w.is_file():
            widget_file = w
        if demo_dir is None and d.is_dir():
            demo_dir = d
        if admin_dir is None and a.is_dir():
            admin_dir = a
        if widget_file and demo_dir and admin_dir:
            break

    if widget_file is not None:
        from fastapi.responses import FileResponse

        widget_path = widget_file  # freeze for closure

        @app.get("/widget.js", include_in_schema=False)
        async def _serve_widget() -> FileResponse:
            return FileResponse(
                widget_path,
                media_type="application/javascript",
                headers={"Cache-Control": "no-store"},
            )
        logger.info("gateway.mount_widget", path=str(widget_file))

    if demo_dir is not None:
        app.mount(
            "/demo",
            StaticFiles(directory=str(demo_dir), html=True),
            name="demo",
        )
        logger.info("gateway.mount_demo", path=str(demo_dir))

    if admin_dir is not None:
        # Note: this mount serves the HTML dashboard at /admin/.
        # The /admin/api/* JSON endpoints are registered as an
        # APIRouter BEFORE this, so FastAPI's router resolves them
        # first and this static mount only catches /admin/,
        # /admin/index.html, /admin/admin.js, etc.
        app.mount(
            "/admin",
            StaticFiles(directory=str(admin_dir), html=True),
            name="admin",
        )
        logger.info("gateway.mount_admin", path=str(admin_dir))


app = create_app()
