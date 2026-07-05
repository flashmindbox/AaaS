"""Smoke tests for the translate HTTP surface.

Runs the app factory with the deterministic mock engine so no model
weights or network are needed — the same wiring the PyInstaller bundle
and CI use. Guards the response shape the widget / exam UI depend on.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.engine.mock import MockTranslateEngine
from app.main import create_app


@pytest.fixture()
def client() -> TestClient:
    app = create_app(
        settings=Settings(engine="mock"), engine=MockTranslateEngine()
    )
    # Context manager runs the lifespan, which flips app.state.ready.
    with TestClient(app) as c:
        yield c


def test_healthz_reports_engine(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "translate", "engine": "mock"}


def test_readyz_after_startup(client: TestClient) -> None:
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


def test_translate_curated_phrase(client: TestClient) -> None:
    r = client.post(
        "/translate",
        json={"text": "My name is Priya", "src_lang": "en", "tgt_lang": "or"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "ମୋ ନାମ ପ୍ରିୟା"
    assert body["src_lang"] == "en"
    assert body["tgt_lang"] == "or"
    assert body["engine"] == "mock"


def test_translate_rejects_oversize_input(client: TestClient) -> None:
    settings = Settings(engine="mock")
    r = client.post(
        "/translate",
        json={
            "text": "x" * (settings.max_input_chars + 1),
            "src_lang": "en",
            "tgt_lang": "or",
        },
    )
    assert r.status_code == 413


def test_translate_rejects_missing_fields(client: TestClient) -> None:
    r = client.post("/translate", json={"text": "hello"})
    assert r.status_code == 422
