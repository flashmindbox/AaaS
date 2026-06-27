"""Shared pytest fixtures for the TTS service.

The real ``MMSEngine`` pulls in torch + transformers and downloads the
MMS-TTS-ory weights, which would make the test suite slow and
network-dependent. We inject a trivial fake in its place — the FastAPI
factory accepts an ``engine=`` override precisely for this.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.engine.base import TTSResult
from app.main import create_app


@dataclass
class FakeEngine:
    """Returns a short deterministic PCM buffer regardless of input.

    Accepts the new ``lang`` arg so the multi-language route works, and
    records it on the call log so tests can assert the right language
    was routed. Also reports the multi-language introspection surface
    (``available_languages``, ``model_id_for``, ``default_language``)
    so the /voices route returns a sensible body under the fake.
    """

    sample_rate: int = 16000
    loaded: bool = field(default=False)
    calls: list[tuple[str, str]] = field(default_factory=list)
    available_languages: list[str] = field(default_factory=lambda: ["or", "hi", "en"])
    default_language: str = "or"

    async def load(self) -> None:
        self.loaded = True
        # Hide the real `_model` attribute the /readyz check looks at.
        self._model = object()  # type: ignore[attr-defined]

    async def warmup(self) -> None:
        pass

    def model_id_for(self, lang: str) -> str:
        return f"fake/mms-{lang}"

    async def synthesise(self, text: str, lang: str = "or") -> TTSResult:
        self.calls.append((text, lang))
        # 0.25 s of silence is enough to exercise header-building and
        # Content-Length bookkeeping without sounding like anything.
        samples = int(self.sample_rate * 0.25)
        pcm = b"\x00\x00" * samples
        return TTSResult(audio=pcm, sample_rate=self.sample_rate,
                         duration_seconds=samples / self.sample_rate)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        aaas_env="test",
        log_level="WARNING",
        model_id="test/fake",
        max_input_chars=100,
        sample_rate=16000,
    )


@pytest.fixture
def engine() -> FakeEngine:
    return FakeEngine()


@pytest.fixture
def app(settings: Settings, engine: FakeEngine) -> FastAPI:
    app = create_app(settings=settings, engine=engine)
    # `get_settings()` is lru_cached and reads the real .env — override
    # so `Depends(get_settings)` resolves to the test Settings instead.
    app.dependency_overrides[get_settings] = lambda: settings
    return app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    # `with` is required so the lifespan runs and `engine.load()` marks
    # the engine ready — otherwise /synthesise would 503.
    with TestClient(app) as c:
        yield c
