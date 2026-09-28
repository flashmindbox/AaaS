"""Result caches for the translate and OCR engines.

IndicTrans2 takes 1–5 s per chunk on CPU and Tesseract ~1 s per page —
and government pages are static, so identical requests repeat
constantly (every browser that opens the demo page re-translates the
same sentences; every rehearsal re-reads the same scanned notice).
These wrappers memoise successful results in a bounded in-memory LRU.
Failures are never cached, and the wrapped engine is otherwise
transparent (``load()``, ``name`` etc. pass through), so tests and
`/healthz` see the real engine.

Translations can additionally persist to a small SQLite file
(``persist_path``) so one rehearsal warms every later run, even across
service restarts. Rows are keyed on the engine name too, so switching
engines (mock → indictrans2) never serves stale output. OCR stays
in-memory only — Tesseract is ~1 s a page, cheap enough to redo.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections import OrderedDict
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

from app.engine.base import Translation
from app.engine.ocr_base import OcrResult


class _Lru:
    """Minimal bounded LRU over an OrderedDict."""

    def __init__(self, maxsize: int) -> None:
        self._maxsize = maxsize
        self._data: OrderedDict[Any, Any] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: Any) -> Any | None:
        try:
            value = self._data.pop(key)
        except KeyError:
            self.misses += 1
            return None
        self._data[key] = value  # re-insert as most recent
        self.hits += 1
        return value

    def put(self, key: Any, value: Any) -> None:
        self._data.pop(key, None)
        self._data[key] = value
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)


class CachingTranslateEngine:
    """Memoises ``translate()`` on (text, src, tgt)."""

    def __init__(
        self, engine: Any, maxsize: int = 2048, persist_path: Path | None = None
    ) -> None:
        self._engine = engine
        self._cache = _Lru(maxsize)
        self._db: sqlite3.Connection | None = None
        if persist_path is not None:
            try:
                persist_path.parent.mkdir(parents=True, exist_ok=True)
                self._db = sqlite3.connect(persist_path, check_same_thread=False)
                self._db.execute(
                    "CREATE TABLE IF NOT EXISTS tr (engine TEXT, src TEXT, tgt TEXT,"
                    " text TEXT, out TEXT, PRIMARY KEY (engine, src, tgt, text))"
                )
                self._db.commit()
            except sqlite3.Error as exc:  # never let the cache block startup
                logger.warning("translate.cache.persist_disabled", error=str(exc))
                self._db = None

    def _engine_name(self) -> str:
        return str(getattr(self._engine, "name", type(self._engine).__name__))

    def _db_get(self, src: str, tgt: str, text: str) -> Translation | None:
        if self._db is None:
            return None
        try:
            row = self._db.execute(
                "SELECT out FROM tr WHERE engine=? AND src=? AND tgt=? AND text=?",
                (self._engine_name(), src, tgt, text),
            ).fetchone()
        except sqlite3.Error:
            return None
        if row is None:
            return None
        return Translation(text=row[0], src_lang=src, tgt_lang=tgt, engine=self._engine_name())

    def _db_put(self, result: Translation, src: str, tgt: str, text: str) -> None:
        # Only persist output the configured engine actually produced — a
        # fallback result (e.g. mock after a model error) must not stick.
        if self._db is None or result.engine != self._engine_name():
            return
        try:
            self._db.execute(
                "INSERT OR REPLACE INTO tr VALUES (?, ?, ?, ?, ?)",
                (self._engine_name(), src, tgt, text, result.text),
            )
            self._db.commit()
        except sqlite3.Error as exc:
            logger.warning("translate.cache.write_failed", error=str(exc))

    def __getattr__(self, item: str) -> Any:
        # load(), name, _model (readyz probing) — everything not defined
        # here belongs to the real engine.
        return getattr(self._engine, item)

    async def translate(self, text: str, *, src_lang: str, tgt_lang: str) -> Translation:
        key = (src_lang, tgt_lang, text)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        stored = self._db_get(src_lang, tgt_lang, text)
        if stored is not None:
            self._cache.put(key, stored)
            return stored
        result = await self._engine.translate(text, src_lang=src_lang, tgt_lang=tgt_lang)
        self._cache.put(key, result)
        self._db_put(result, src_lang, tgt_lang, text)
        return result


class CachingOcrEngine:
    """Memoises ``recognize()`` on (sha256(bytes), media_type, lang)."""

    def __init__(self, engine: Any, maxsize: int = 128) -> None:
        self._engine = engine
        self._cache = _Lru(maxsize)

    def __getattr__(self, item: str) -> Any:
        return getattr(self._engine, item)

    async def recognize(self, data: bytes, *, media_type: str, lang: str) -> OcrResult:
        key = (hashlib.sha256(data).hexdigest(), media_type, lang.lower())
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        result = await self._engine.recognize(data, media_type=media_type, lang=lang)
        self._cache.put(key, result)
        return result
