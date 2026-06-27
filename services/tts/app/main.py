"""FastAPI factory for the TTS service.

Same shape as the gateway's factory so tests and wiring look familiar:
``create_app`` takes optional overrides; an app-level lifespan owns the
model (heavy to build, expensive to keep) and closes it on shutdown.

The real model is only loaded when the lifespan runs. Tests can inject
an in-memory fake via ``engine=`` so the pytest suite stays under a
second.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app import __version__
from app.config import Settings, get_settings
from app.engine.base import TTSEngine
from app.engine.multi import MultiLangMMSEngine
from app.routes import health, synthesise

# The three MMS-TTS checkpoints are bundled on disk (services/tts/models/),
# so model loading must never reach out to the Hugging Face Hub. Without
# these, transformers issues blocking HEAD/GET calls to huggingface.co on
# every (lazy) model load — adding seconds of latency on a slow network and
# hanging the first request for a secondary language outright on an offline
# laptop. The .run-logs show this happening on every load, with an
# "unauthenticated requests to the HF Hub" warning. setdefault so a
# maintainer can still force a re-download by exporting HF_HUB_OFFLINE=0.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

logger = structlog.get_logger(__name__)


def _configure_logging(level: str) -> None:
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


def _build_engine(settings: Settings) -> MultiLangMMSEngine:
    # If the legacy ``model_id`` override is set, it should win for the
    # default language — that way ``AAAS_TTS_MODEL_ID=/path/to/custom``
    # still picks up the new checkpoint for Odia without breaking the
    # other two languages.
    language_models = dict(settings.language_models)
    if settings.model_id and settings.default_language in language_models:
        language_models[settings.default_language] = settings.model_id
    return MultiLangMMSEngine(
        language_models=language_models,
        default_language=settings.default_language,
        cache_dir=settings.model_cache_dir,
        sample_rate=settings.sample_rate,
        chunk_chars=settings.chunk_chars,
    )


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine: TTSEngine = app.state.engine
    # Only call load() on backends that actually need it. The Protocol
    # doesn't require `load`, so guard with `hasattr` — this keeps fake
    # engines in tests trivial (no load step, no warmup).
    if hasattr(engine, "load"):
        await engine.load()
    if hasattr(engine, "warmup"):
        try:
            await engine.warmup()
        except Exception as exc:  # noqa: BLE001
            # A failed warmup shouldn't take the service down; the first
            # real request will just pay the JIT cost.
            logger.warning("tts.warmup_failed", error=str(exc))
    logger.info(
        "tts.start",
        version=__version__,
        env=settings.aaas_env,
        port=settings.tts_port,
        model=settings.model_id,
    )
    try:
        yield
    finally:
        logger.info("tts.stop")


def create_app(
    settings: Settings | None = None,
    engine: TTSEngine | None = None,
) -> FastAPI:
    """Build the TTS FastAPI app.

    ``engine`` is injectable so tests can swap in a fake that returns a
    fixed PCM buffer — avoids loading 150 MB of weights for every run.
    """
    settings = settings or get_settings()
    _configure_logging(settings.log_level)

    app = FastAPI(
        title="AaaS TTS",
        version=__version__,
        description=(
            "Offline Odia / Hindi / English text-to-speech powered by "
            "Meta MMS-TTS. Default language's model is eager-loaded; "
            "other languages lazy-load on first request. "
            "POST /synthesise → audio/wav."
        ),
        lifespan=_lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine if engine is not None else _build_engine(settings)
    app.include_router(health.router)
    app.include_router(synthesise.router)
    return app


app = create_app()
