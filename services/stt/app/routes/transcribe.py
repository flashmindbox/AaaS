"""POST /transcribe — audio upload → JSON transcript.

Accepts multipart/form-data with an ``audio`` file field (WAV/OGG/webm;
decoding is the engine's job). An optional ``language`` form field
hints the engine; engines that don't support hints ignore it.

Behaviour is deliberately forgiving: any decoder failure comes back as
400 with a structured JSON error rather than a 500, so the widget knows
to fall back to keyboard input without burning a ticket on the judge.
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel

from app.engine.base import Transcript

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["stt"])


class TranscribeResponse(BaseModel):
    text: str
    language: str
    confidence: float
    engine: str


def _to_response(t: Transcript) -> TranscribeResponse:
    return TranscribeResponse(
        text=t.text,
        language=t.language,
        confidence=t.confidence,
        engine=t.engine,
    )


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    request: Request,
    audio: Annotated[UploadFile, File(description="WAV/OGG/webm audio blob")],
    language: Annotated[str | None, Form()] = None,
) -> TranscribeResponse:
    data = await audio.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio payload",
        )
    try:
        result = await request.app.state.engine.transcribe(
            data, language_hint=language
        )
    except RuntimeError as exc:
        # Engine not loaded yet (bundle cold start), or decoder failure.
        logger.warning("stt.transcribe_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"STT temporarily unavailable: {exc!s}",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.warning("stt.transcribe_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not decode audio: {exc!s}",
        ) from exc
    return _to_response(result)
