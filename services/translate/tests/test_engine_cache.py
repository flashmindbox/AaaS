"""Unit tests for the translate/OCR result caches."""

from __future__ import annotations

import pytest

from app.engine.base import Translation
from app.engine.cache import CachingOcrEngine, CachingTranslateEngine, _Lru
from app.engine.ocr_base import OcrPage, OcrResult


class CountingTranslate:
    name = "counting"

    def __init__(self) -> None:
        self.calls = 0

    async def translate(self, text: str, *, src_lang: str, tgt_lang: str) -> Translation:
        self.calls += 1
        return Translation(text=text.upper(), src_lang=src_lang, tgt_lang=tgt_lang, engine=self.name)


class CountingOcr:
    name = "counting-ocr"

    def __init__(self) -> None:
        self.calls = 0

    async def recognize(self, data: bytes, *, media_type: str, lang: str) -> OcrResult:
        self.calls += 1
        return OcrResult(text="hello", pages=[OcrPage(page=1, text="hello", source="ocr")], lang=lang, engine=self.name)


class FailingTranslate:
    name = "failing"

    def __init__(self) -> None:
        self.calls = 0

    async def translate(self, text: str, *, src_lang: str, tgt_lang: str) -> Translation:
        self.calls += 1
        raise RuntimeError("engine down")


@pytest.mark.asyncio
async def test_translate_cache_hits_on_repeat() -> None:
    inner = CountingTranslate()
    engine = CachingTranslateEngine(inner)
    a = await engine.translate("hello", src_lang="en", tgt_lang="or")
    b = await engine.translate("hello", src_lang="en", tgt_lang="or")
    assert inner.calls == 1
    assert a is b


@pytest.mark.asyncio
async def test_translate_cache_keys_on_langs() -> None:
    inner = CountingTranslate()
    engine = CachingTranslateEngine(inner)
    await engine.translate("hello", src_lang="en", tgt_lang="or")
    await engine.translate("hello", src_lang="en", tgt_lang="hi")
    assert inner.calls == 2


@pytest.mark.asyncio
async def test_failures_are_never_cached() -> None:
    inner = FailingTranslate()
    engine = CachingTranslateEngine(inner)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await engine.translate("x", src_lang="en", tgt_lang="or")
    assert inner.calls == 2


@pytest.mark.asyncio
async def test_attribute_passthrough() -> None:
    inner = CountingTranslate()
    engine = CachingTranslateEngine(inner)
    assert engine.name == "counting"


@pytest.mark.asyncio
async def test_ocr_cache_keys_on_content_hash() -> None:
    inner = CountingOcr()
    engine = CachingOcrEngine(inner)
    await engine.recognize(b"same-bytes", media_type="image/png", lang="en")
    await engine.recognize(b"same-bytes", media_type="image/png", lang="en")
    await engine.recognize(b"other-bytes", media_type="image/png", lang="en")
    assert inner.calls == 2


def test_lru_evicts_oldest() -> None:
    lru = _Lru(2)
    lru.put("a", 1)
    lru.put("b", 2)
    assert lru.get("a") == 1  # refresh a
    lru.put("c", 3)           # evicts b
    assert lru.get("b") is None
    assert lru.get("a") == 1
    assert lru.get("c") == 3
