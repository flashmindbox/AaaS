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

import numpy as np
import structlog

from app.engine.base import TTSResult
from app.engine.mms import EmptyTokenisationError, MMSEngine
from app.textnorm import split_script_runs, verbalize_numbers

logger = structlog.get_logger(__name__)

# Silence spliced between fragments of different languages — same
# rationale as the inter-chunk silence in MMSEngine.
_INTER_RUN_SILENCE_MS = 100


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
        """Speak ``text``, handling what the checkpoints can't.

        Each MMS vocabulary is tiny (the Odia one has no digits and no
        Latin letters — unknown characters are silently DROPPED by the
        tokeniser), so before synthesis the text is split into script
        runs and every run has its numbers/symbols verbalised in that
        run's language. Runs are then spoken by their own checkpoint
        and spliced — an English school name inside an Odia notice is
        read by the English voice instead of vanishing.
        """
        if lang not in self._language_models:
            # Preserve the old error for unconfigured languages.
            await self._ensure_loaded(lang)
        runs = split_script_runs(text, primary=lang)
        # Only keep runs for languages we can actually speak; foreign
        # scripts we have no model for fall back to the request lang
        # (they'll mostly drop, same as before — nothing worse).
        runs = [(rl if rl in self._language_models else lang, rt) for rl, rt in runs]
        if not runs:
            runs = [(lang, text)]
        if len(runs) == 1:
            run_lang, run_text = runs[0]
            engine = await self._ensure_loaded(run_lang)
            return await engine.synthesise(verbalize_numbers(run_text, run_lang), run_lang)

        parts: list[np.ndarray] = []
        sample_rate = self.sample_rate
        total_duration = 0.0
        spoken = 0
        for i, (run_lang, run_text) in enumerate(runs):
            engine = await self._ensure_loaded(run_lang)
            try:
                result = await engine.synthesise(
                    verbalize_numbers(run_text, run_lang), run_lang
                )
            except EmptyTokenisationError:
                # A run of pure punctuation/OCR junk — skip it rather
                # than failing the whole utterance.
                continue
            sample_rate = result.sample_rate
            parts.append(np.frombuffer(result.audio, dtype=np.int16))
            total_duration += result.duration_seconds
            spoken += 1
            if i < len(runs) - 1:
                parts.append(
                    np.zeros(int(sample_rate * _INTER_RUN_SILENCE_MS / 1000), dtype=np.int16)
                )
        if not spoken:
            raise EmptyTokenisationError(
                "No fragment of the input could be synthesised by any voice."
            )
        pcm = np.concatenate(parts).tobytes()
        logger.info(
            "tts.mixed_script",
            runs=len(runs),
            spoken=spoken,
            langs=sorted({rl for rl, _ in runs}),
        )
        return TTSResult(
            audio=pcm,
            sample_rate=sample_rate,
            duration_seconds=len(pcm) / (2 * sample_rate),
        )

    # -- introspection (routes/voices) -----------------------------------

    @property
    def available_languages(self) -> list[str]:
        return sorted(self._language_models)

    def model_id_for(self, lang: str) -> str:
        return self._language_models[lang]

    @property
    def default_language(self) -> str:
        return self._default_language
