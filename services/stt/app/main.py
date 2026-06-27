"""FastAPI factory for the AaaS STT service.

Lifespan owns the engine: it calls ``engine.load()`` (if defined), flips
``app.state.ready = True``, and keeps the model resident for the life
of the process.

Engine selection is by env var — see :mod:`app.config`. Tests inject a
fake engine via ``create_app(engine=...)`` so the suite doesn't need
1 GB of torch wheels.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app import __version__
from app.config import Settings, get_settings
from app.engine.base import STTEngine
from app.routes import health, transcribe

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


def _build_default_engine(settings: Settings) -> STTEngine:
    """Pick the engine named in ``AAAS_STT_ENGINE``.

    Default is ``indic_wav2vec`` so source builds transcribe real Odia
    audio out of the box. Without the ``[indic]`` extras installed the
    import inside ``load()`` raises, the lifespan catches it, and falls
    back to the mock engine — so a vanilla ``pip install -e .`` still
    boots cleanly, just with canned transcripts.
    """
    if settings.engine == "indic_wav2vec":
        from app.engine.indic_wav2vec import IndicWav2VecEngine

        return IndicWav2VecEngine(cache_dir=settings.model_cache_dir)
    if settings.engine == "whisper":
        from app.engine.whisper import WhisperEngine

        return WhisperEngine(cache_dir=settings.model_cache_dir)
    from app.engine.mock import MockSTTEngine

    return MockSTTEngine()


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine: STTEngine = app.state.engine
    app.state.ready = False
    if hasattr(engine, "load"):
        try:
            await engine.load()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "stt.engine_load_failed", engine=type(engine).__name__, error=str(exc)
            )
            # Fall back to mock so the service still serves traffic.
            from app.engine.mock import MockSTTEngine

            app.state.engine = MockSTTEngine()
    app.state.ready = True
    logger.info(
        "stt.start",
        version=__version__,
        env=settings.aaas_env,
        port=settings.stt_port,
        engine=type(app.state.engine).__name__,
    )
    try:
        yield
    finally:
        logger.info("stt.stop")


def create_app(
    settings: Settings | None = None,
    engine: STTEngine | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    _configure_logging(settings.log_level)

    app = FastAPI(
        title="AaaS STT",
        version=__version__,
        description=(
            "Speech-to-text service for Odia (IndicWav2Vec), "
            "English / Hindi (faster-whisper), or a mock engine for "
            "demos. POST /transcribe → JSON transcript."
        ),
        lifespan=_lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine if engine is not None else _build_default_engine(settings)
    app.include_router(health.router)
    app.include_router(transcribe.router)
    return app


app = create_app()
