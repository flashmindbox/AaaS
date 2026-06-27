"""POST /translate — JSON in, JSON out.

Accepts:

    {"text": "...", "src_lang": "or", "tgt_lang": "en"}

Returns:

    {"text": "...", "src_lang": "or", "tgt_lang": "en", "engine": "mock"}

Shape is stable across engines so the widget / exam UI doesn't care
which backend is loaded.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.config import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["translate"])


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    src_lang: str = Field(..., min_length=2, max_length=10)
    tgt_lang: str = Field(..., min_length=2, max_length=10)


class TranslateResponse(BaseModel):
    text: str
    src_lang: str
    tgt_lang: str
    engine: str


@router.post("/translate", response_model=TranslateResponse)
async def translate(
    request: Request, payload: TranslateRequest
) -> TranslateResponse:
    settings = get_settings()
    if len(payload.text) > settings.max_input_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Text exceeds {settings.max_input_chars} chars",
        )
    try:
        result = await request.app.state.engine.translate(
            payload.text, src_lang=payload.src_lang, tgt_lang=payload.tgt_lang
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    return TranslateResponse(
        text=result.text,
        src_lang=result.src_lang,
        tgt_lang=result.tgt_lang,
        engine=result.engine,
    )
