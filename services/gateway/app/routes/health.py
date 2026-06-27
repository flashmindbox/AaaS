"""Liveness, readiness, and version endpoints.

Kubernetes (Phase 5) will probe `/healthz` for liveness and `/readyz` for
readiness. `/version` is a human-friendly sanity check during incident
response. None of these require auth.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__

router = APIRouter(tags=["ops"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["gateway"]


class VersionResponse(BaseModel):
    service: Literal["gateway"]
    version: str


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    """Liveness — process is up. Does not check downstream deps."""
    return HealthResponse(status="ok", service="gateway")


@router.get("/version", response_model=VersionResponse)
async def version() -> VersionResponse:
    """Reports the running build. Useful during incident triage."""
    return VersionResponse(service="gateway", version=__version__)
