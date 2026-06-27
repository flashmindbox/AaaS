"""Liveness / readiness endpoints.

``/healthz`` returns as soon as the process is up — the gateway can
route traffic to us. ``/readyz`` only flips to ``ok`` after the TTS
model has finished loading, so the orchestrator (or a smoke test) knows
when it's safe to hit ``/synthesise``.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from app import __version__

router = APIRouter(tags=["meta"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "tts"}


@router.get("/readyz")
async def readyz(request: Request) -> Response:
    engine = getattr(request.app.state, "engine", None)
    if engine is None or getattr(engine, "_model", None) is None:
        return Response(
            content='{"status":"loading"}',
            media_type="application/json",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response(
        content='{"status":"ok"}',
        media_type="application/json",
    )


@router.get("/version")
async def version() -> dict[str, str]:
    return {"version": __version__, "service": "tts"}
