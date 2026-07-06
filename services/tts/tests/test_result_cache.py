"""The multi-engine result cache: identical requests synthesise once."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.base import TTSResult
from app.engine.multi import MultiLangMMSEngine


class CountingEngine:
    sample_rate = 16000

    def __init__(self) -> None:
        self.calls = 0

    async def synthesise(self, text: str, lang: str = "or") -> TTSResult:
        self.calls += 1
        return TTSResult(audio=b"\x00\x00" * 100, sample_rate=16000, duration_seconds=0.01)


@pytest.fixture()
def engine(monkeypatch: pytest.MonkeyPatch) -> tuple[MultiLangMMSEngine, CountingEngine]:
    multi = MultiLangMMSEngine(
        language_models={"or": "fake/or", "en": "fake/en"},
        default_language="or",
        cache_dir=Path("."),
        sample_rate=16000,
    )
    counting = CountingEngine()

    async def _fake_ensure(lang: str) -> CountingEngine:
        return counting

    monkeypatch.setattr(multi, "_ensure_loaded", _fake_ensure)
    return multi, counting


@pytest.mark.asyncio
async def test_identical_requests_synthesise_once(engine) -> None:
    multi, counting = engine
    a = await multi.synthesise("ନମସ୍କାର ଜଜପୁର", "or")
    b = await multi.synthesise("ନମସ୍କାର ଜଜପୁର", "or")
    assert counting.calls == 1
    assert a is b


@pytest.mark.asyncio
async def test_cache_keys_on_lang(engine) -> None:
    multi, counting = engine
    await multi.synthesise("Hello there", "en")
    await multi.synthesise("Hello there", "or")
    assert counting.calls == 2


@pytest.mark.asyncio
async def test_mixed_script_result_is_cached(engine) -> None:
    multi, counting = engine
    await multi.synthesise("ପରିଚାଳିତ SCHOOL ଦ୍ୱାରା", "or")
    first = counting.calls
    assert first >= 2  # one call per script run
    await multi.synthesise("ପରିଚାଳିତ SCHOOL ଦ୍ୱାରା", "or")
    assert counting.calls == first  # whole utterance served from cache
