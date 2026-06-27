"""/synthesise — the one endpoint that actually matters.

Contract:

- ``POST /synthesise`` with ``{"text": "...", "lang": "or"}`` →
  ``audio/wav`` body. ``lang`` is optional and defaults to the
  service's configured default (Odia in Phase A).
- ``GET  /voices`` → JSON describing every language the service can
  speak, so the widget can disable picker options that aren't wired up.

We accept and honour ``X-Tenant-*`` headers (set by the gateway) but
don't need them for anything beyond logging right now. They're kept in
the log line so audit trails in Phase 1.3 can join requests across
services.
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.audio import pcm16_to_wav
from app.config import Settings, get_settings
from app.engine.base import TTSEngine
from app.engine.mms import EmptyTokenisationError
from app.engine.multi import UnsupportedLanguageError

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["tts"])


class SynthesiseRequest(BaseModel):
    text: str = Field(
        ..., min_length=1,
        description="Text to synthesise. Must match the script implied by ``lang``.",
    )
    lang: str | None = Field(
        default=None,
        pattern=r"^[a-z]{2,3}$",
        description=(
            "ISO-639-1 language code: 'or' (Odia), 'hi' (Hindi), or 'en' "
            "(English). Omit to use the service default."
        ),
    )


class VoiceInfo(BaseModel):
    lang: str
    model: str


class VoicesResponse(BaseModel):
    # Legacy fields — kept for any existing client that reads `.model`
    # or `.language` directly. `default_language` and `voices` carry the
    # new multi-language surface.
    model: str
    language: str
    default_language: str
    voices: list[VoiceInfo]
    sample_rate: int
    max_input_chars: int


def _get_engine(request: Request) -> TTSEngine:
    engine: TTSEngine | None = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TTS engine not ready",
        )
    return engine


@router.get("/voices", response_model=VoicesResponse)
async def voices(
    engine: Annotated[TTSEngine, Depends(_get_engine)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> VoicesResponse:
    # Multi-engine exposes the full language map; fall back gracefully
    # if a single-model engine is plugged in (e.g. tests with FakeEngine).
    available = getattr(engine, "available_languages", [settings.default_language])
    default_lang = getattr(engine, "default_language", settings.default_language)
    voice_list: list[VoiceInfo] = []
    for lang in available:
        getter = getattr(engine, "model_id_for", None)
        model_id = getter(lang) if callable(getter) else settings.model_id
        voice_list.append(VoiceInfo(lang=lang, model=model_id))
    return VoicesResponse(
        model=settings.model_id,
        language="ory",  # legacy: ISO 639-3 for Odia
        default_language=default_lang,
        voices=voice_list,
        sample_rate=settings.sample_rate,
        max_input_chars=settings.max_input_chars,
    )


@router.post("/synthesise")
async def synthesise(
    payload: SynthesiseRequest,
    engine: Annotated[TTSEngine, Depends(_get_engine)],
    settings: Annotated[Settings, Depends(get_settings)],
    x_tenant_slug: Annotated[str | None, Header(alias="X-Tenant-Slug")] = None,
) -> Response:
    text = payload.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="text is empty"
        )
    if len(text) > settings.max_input_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"text exceeds max_input_chars={settings.max_input_chars}",
        )
    lang = (payload.lang or settings.default_language).lower()
    try:
        result = await engine.synthesise(text, lang)
    except UnsupportedLanguageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except EmptyTokenisationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    logger.info(
        "tts.request",
        tenant=x_tenant_slug,
        lang=lang,
        chars=len(text),
        audio_seconds=round(result.duration_seconds, 2),
    )
    wav = pcm16_to_wav(result.audio, result.sample_rate)
    return Response(
        content=wav,
        media_type="audio/wav",
        headers={
            "Cache-Control": "no-store",
            "X-Audio-Duration": f"{result.duration_seconds:.3f}",
            "X-Sample-Rate": str(result.sample_rate),
            "X-Lang": lang,
        },
    )
