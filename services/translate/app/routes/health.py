"""Liveness and readiness for the translate service."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import __version__

router = APIRouter(tags=["ops"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["translate"]
    engine: str


@router.get("/healthz", response_model=HealthResponse)
async def healthz(request: Request) -> HealthResponse:
    return HealthResponse(
        status="ok", service="translate", engine=request.app.state.engine.name
    )


@router.get("/readyz")
async def readyz(request: Request) -> JSONResponse:
    if getattr(request.app.state, "ready", False):
        return JSONResponse({"status": "ready"})
    return JSONResponse(
        {"status": "loading"},
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@router.get("/version")
async def version() -> dict[str, str]:
    return {"service": "translate", "version": __version__}
