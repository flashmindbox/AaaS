"""Liveness + readiness endpoints (mirrors the TTS and gateway layout)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import __version__

router = APIRouter(tags=["ops"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["stt"]
    engine: str


@router.get("/healthz", response_model=HealthResponse)
async def healthz(request: Request) -> HealthResponse:
    engine = request.app.state.engine
    return HealthResponse(status="ok", service="stt", engine=engine.name)


@router.get("/readyz")
async def readyz(request: Request) -> JSONResponse:
    """Ready when the engine has finished its load() step.

    The lifespan sets ``app.state.ready = True`` once the backend's
    model is warm. Until then we return 503 so the orchestrator's
    wait-ready probe keeps looping.
    """
    if getattr(request.app.state, "ready", False):
        return JSONResponse({"status": "ready"})
    return JSONResponse(
        {"status": "loading"},
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@router.get("/version")
async def version() -> dict[str, str]:
    return {"service": "stt", "version": __version__}
