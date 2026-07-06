"""POST /simplify — JSON in, JSON out.

Accepts:

    {"text": "...", "lang": "en"}

Returns:

    {"text": "...", "lang": "en", "engine": "rules"}

Powers the widget's "Easy Read" mode. Shape is stable across engines so
the rule-based engine can be swapped for an LLM later without touching
the widget. Reached through the gateway at /translate/simplify (the
gateway's catch-all proxy forwards any /translate/* suffix here).
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.config import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["simplify"])


class SimplifyRequest(BaseModel):
    text: str = Field(..., min_length=1)
    lang: str = Field(..., min_length=2, max_length=10)


class SimplifyResponse(BaseModel):
    text: str
    lang: str
    engine: str


@router.post("/simplify", response_model=SimplifyResponse)
async def simplify(
    request: Request, payload: SimplifyRequest
) -> SimplifyResponse:
    settings = get_settings()
    if len(payload.text) > settings.max_input_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Text exceeds {settings.max_input_chars} chars",
        )
    try:
        result = await request.app.state.simplify_engine.simplify(
            payload.text, lang=payload.lang
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    return SimplifyResponse(
        text=result.text,
        lang=result.lang,
        engine=result.engine,
    )
