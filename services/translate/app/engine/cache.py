"""Result caches for the translate and OCR engines.

IndicTrans2 takes 1–5 s per chunk on CPU and Tesseract ~1 s per page —
and government pages are static, so identical requests repeat
constantly (every browser that opens the demo page re-translates the
same sentences; every rehearsal re-reads the same scanned notice).
These wrappers memoise successful results in a bounded in-memory LRU.
Failures are never cached, and the wrapped engine is otherwise
transparent (``load()``, ``name`` etc. pass through), so tests and
`/healthz` see the real engine.

Deliberately in-memory only: results die with the process, which is
exactly right for a dev/demo service — no invalidation story needed.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from typing import Any

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

    def __init__(self, engine: Any, maxsize: int = 2048) -> None:
        self._engine = engine
        self._cache = _Lru(maxsize)

    def __getattr__(self, item: str) -> Any:
        # load(), name, _model (readyz probing) — everything not defined
        # here belongs to the real engine.
        return getattr(self._engine, item)

    async def translate(self, text: str, *, src_lang: str, tgt_lang: str) -> Translation:
        key = (src_lang, tgt_lang, text)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        result = await self._engine.translate(text, src_lang=src_lang, tgt_lang=tgt_lang)
        self._cache.put(key, result)
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
