"""Multi-language wrapper around several :class:`MMSEngine` instances.

Ships three Meta MMS-TTS checkpoints so the widget's language picker
actually does something:

    or  ->  facebook/mms-tts-ory   (Odia)
    hi  ->  facebook/mms-tts-hin   (Hindi)
    en  ->  facebook/mms-tts-eng   (English)

Only the *default* language's weights are eager-loaded during lifespan
startup — the others lazy-load on first request. Rationale:

- A judge-laptop cold start with three models loading serially would
  add ~20 s to the pre-demo wait; unacceptable for the 60-120 s target
  in ``docs/demo-rehearsal-checklist.md``.
- Each VITS-small checkpoint is ~150 MB resident. Keeping secondary
  languages on disk until needed cuts idle-memory to one model.
- First-request latency for a secondary language is still a one-time
  cost per server lifetime. The UI shows "Synthesising (1/N)…" during
  that window so it doesn't look hung.

Concurrency: a per-language load-lock prevents two parallel requests
from racing the ``from_pretrained`` call on the same model.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import structlog

from app.engine.base import TTSResult
from app.engine.mms import MMSEngine

logger = structlog.get_logger(__name__)


class UnsupportedLanguageError(ValueError):
    """Raised when a caller asks for a language not in ``language_models``."""


class MultiLangMMSEngine:
    """Routes ``synthesise(text, lang)`` to a per-language MMSEngine."""

    sample_rate: int

    def __init__(
        self,
        *,
        language_models: dict[str, str],
        default_language: str,
        cache_dir: Path,
        sample_rate: int,
        chunk_chars: int = 180,
    ) -> None:
        if default_language not in language_models:
            raise ValueError(
                f"default_language {default_language!r} not in language_models "
                f"{list(language_models)!r}"
            )
        self._language_models = dict(language_models)
        self._default_language = default_language
        self._cache_dir = cache_dir
        self.sample_rate = sample_rate
        self._chunk_chars = chunk_chars
        self._engines: dict[str, MMSEngine] = {}
        # One lock *per language* so warm Odia traffic doesn't block
        # while Hindi is loading for the first time.
        self._load_locks: dict[str, asyncio.Lock] = {}
        # Preserve the "has this been loaded?" signal the /readyz route
        # inspects via ``getattr(engine, "_model", None)``. We proxy that
        # by exposing the default-language engine's ``_model`` attribute
        # once it exists.
        self._model: object | None = None

    # -- lifespan --------------------------------------------------------

    async def load(self) -> None:
        """Eager-load only the default language. Others wait until their
        first request — see module docstring."""
        await self._ensure_loaded(self._default_language)
        self._model = self._engines[self._default_language]._model

    async def warmup(self) -> None:
        await self._engines[self._default_language].warmup(self._default_language)

    # -- internals -------------------------------------------------------

    def _make_engine(self, lang: str) -> MMSEngine:
        model_id = self._language_models[lang]
        return MMSEngine(
            model_id=model_id,
            cache_dir=self._cache_dir,
            sample_rate=self.sample_rate,
            chunk_chars=self._chunk_chars,
        )

    async def _ensure_loaded(self, lang: str) -> MMSEngine:
        if lang not in self._language_models:
            raise UnsupportedLanguageError(
                f"lang {lang!r} not configured. "
                f"Available: {sorted(self._language_models)}"
            )
        engine = self._engines.get(lang)
        if engine is not None:
            return engine
        lock = self._load_locks.setdefault(lang, asyncio.Lock())
        async with lock:
            engine = self._engines.get(lang)
            if engine is not None:
                return engine
            logger.info(
                "tts.lazy_load",
                lang=lang,
                model_id=self._language_models[lang],
            )
            engine = self._make_engine(lang)
            await engine.load()
            self._engines[lang] = engine
            return engine

    # -- protocol --------------------------------------------------------

    async def synthesise(self, text: str, lang: str = "or") -> TTSResult:
        engine = await self._ensure_loaded(lang)
        return await engine.synthesise(text, lang)

    # -- introspection (routes/voices) -----------------------------------

    @property
    def available_languages(self) -> list[str]:
        return sorted(self._language_models)

    def model_id_for(self, lang: str) -> str:
        return self._language_models[lang]

    @property
    def default_language(self) -> str:
        return self._default_language
