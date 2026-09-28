"""FastAPI factory for the Translation service."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI

from app import __version__
from app.config import Settings, get_settings
from app.engine.base import TranslateEngine
from app.engine.cache import CachingOcrEngine, CachingTranslateEngine
from app.engine.ocr_base import OcrEngine
from app.engine.simplify_base import SimplifyEngine
from app.engine.simplify_rules import RuleSimplifyEngine
from app.routes import health, ocr, simplify, translate

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


def _build_default_engine(settings: Settings) -> TranslateEngine:
    if settings.engine == "google":
        from app.engine.google import GoogleTranslateEngine

        return GoogleTranslateEngine()
    if settings.engine == "nllb":
        from app.engine.nllb import NllbEngine

        return NllbEngine(cache_dir=settings.model_cache_dir)
    if settings.engine == "indictrans2":
        from app.engine.indictrans2 import IndicTrans2Engine

        return IndicTrans2Engine(cache_dir=settings.model_cache_dir)
    from app.engine.mock import MockTranslateEngine

    return MockTranslateEngine()


def _build_default_ocr_engine(settings: Settings) -> OcrEngine:
    """OCR engine per config. Unlike translation, a load failure DOES
    fall back to the mock (in _lifespan): OCR is an add-on capability —
    a missing tesseract binary must never take down translate/simplify,
    and the mock keeps the demo alive on a fresh machine."""
    if settings.ocr_engine == "tesseract":
        try:
            from app.engine.ocr_tesseract import TesseractOcrEngine

            tessdata = settings.tessdata_dir
            if not tessdata:
                default_dir = Path(settings.model_cache_dir) / "tessdata"
                if default_dir.is_dir():
                    tessdata = str(default_dir.resolve())
            return TesseractOcrEngine(
                tesseract_cmd=settings.tesseract_cmd,
                tessdata_dir=tessdata,
                max_pages=settings.ocr_max_pages,
            )
        except ImportError as exc:
            logger.warning(
                "translate.ocr_extras_missing",
                error=str(exc),
                hint="pip install -e .[ocr] for real OCR; using mock",
            )
    from app.engine.ocr_mock import MockOcrEngine

    return MockOcrEngine()


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine: TranslateEngine = app.state.engine
    app.state.ready = False
    app.state.load_error = None
    # OCR loads first and independently: a missing tesseract binary
    # swaps in the mock (STT-style fallback) and never affects the
    # translation engine's readiness below.
    ocr_engine = app.state.ocr_engine
    if hasattr(ocr_engine, "load"):
        try:
            await ocr_engine.load()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "translate.ocr_engine_load_failed",
                engine=type(ocr_engine).__name__,
                error=str(exc),
                hint=(
                    "install tesseract (winget install UB-Mannheim.TesseractOCR) "
                    "and run bundle/prefetch_tessdata.py; using mock OCR"
                ),
            )
            from app.engine.ocr_mock import MockOcrEngine

            app.state.ocr_engine = MockOcrEngine()
    if hasattr(engine, "load"):
        try:
            await engine.load()
        except Exception as exc:  # noqa: BLE001
            # Do NOT silently swap in the mock engine — that hides the
            # failure from the widget, which can only see /readyz and
            # the /translate response. The service stays unready, the
            # gateway's 503 surfaces in the widget as
            # "Translation unavailable", and the operator fixes the
            # actual cause (missing [indic] extras, missing weights,
            # out-of-memory, etc.) instead of getting a broken demo
            # that looks fine.
            logger.error(
                "translate.engine_load_failed",
                engine=type(engine).__name__,
                error=str(exc),
                hint=(
                    "install `.[indic]` extras and prefetch models with "
                    "`python services/translate/bundle/prefetch_model.py`, "
                    "or set AAAS_TRANSLATE_ENGINE=mock to force the mock corpus"
                ),
            )
            app.state.load_error = str(exc)
            try:
                yield
            finally:
                logger.info("translate.stop")
            return
    app.state.ready = True
    logger.info(
        "translate.start",
        version=__version__,
        env=settings.aaas_env,
        port=settings.translate_port,
        engine=type(app.state.engine).__name__,
    )
    try:
        yield
    finally:
        logger.info("translate.stop")


def create_app(
    settings: Settings | None = None,
    engine: TranslateEngine | None = None,
    simplify_engine: SimplifyEngine | None = None,
    ocr_engine: OcrEngine | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    _configure_logging(settings.log_level)

    app = FastAPI(
        title="AaaS Translation",
        version=__version__,
        description=(
            "Indic↔English translation for the AaaS gateway. Defaults to "
            "AI4Bharat IndicTrans2 distilled-200M; falls back to a curated "
            "mock corpus if the [indic] extras aren't installed."
        ),
        lifespan=_lifespan,
    )
    app.state.settings = settings
    # Both slow engines are wrapped in bounded result caches: identical
    # requests repeat constantly (static pages, demo rehearsals) and
    # IndicTrans2/Tesseract pay seconds each time. Simplify stays
    # uncached — the rules run in microseconds.
    # Only the real, settings-built engine persists — injected (test)
    # engines keep a purely in-memory cache.
    persist = (
        Path(settings.result_cache_path)
        if engine is None and settings.result_cache_path
        else None
    )
    app.state.engine = CachingTranslateEngine(
        engine if engine is not None else _build_default_engine(settings),
        persist_path=persist,
    )
    # Rule-based, no model weights, no load() — ready at import. An LLM
    # engine can be injected here later without touching the route.
    app.state.simplify_engine = simplify_engine if simplify_engine is not None else RuleSimplifyEngine()
    app.state.ocr_engine = CachingOcrEngine(
        ocr_engine if ocr_engine is not None else _build_default_ocr_engine(settings)
    )
    app.include_router(health.router)
    app.include_router(translate.router)
    app.include_router(simplify.router)
    app.include_router(ocr.router)
    return app


app = create_app()
