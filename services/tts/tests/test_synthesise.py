"""End-to-end tests for the TTS routes, using the FakeEngine fixture."""

from __future__ import annotations

import struct

from fastapi.testclient import TestClient

from tests.conftest import FakeEngine


def test_healthz_is_open(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "tts"}


def test_voices_reports_settings(client: TestClient) -> None:
    response = client.get("/voices")
    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "ory"
    assert body["sample_rate"] == 16000
    assert body["max_input_chars"] == 100
    assert body["default_language"] == "or"
    langs = {v["lang"] for v in body["voices"]}
    assert langs == {"or", "hi", "en"}


def test_synthesise_returns_wav(client: TestClient, engine: FakeEngine) -> None:
    response = client.post("/synthesise", json={"text": "ନମସ୍କାର"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.headers["x-lang"] == "or"
    # RIFF/WAV magic
    assert response.content[:4] == b"RIFF"
    assert response.content[8:12] == b"WAVE"
    # Sample rate little-endian at byte 24
    (rate,) = struct.unpack("<I", response.content[24:28])
    assert rate == 16000
    # Default lang = "or" when client omits it.
    assert engine.calls == [("ନମସ୍କାର", "or")]


def test_synthesise_routes_by_lang(client: TestClient, engine: FakeEngine) -> None:
    r = client.post("/synthesise", json={"text": "Hello world", "lang": "en"})
    assert r.status_code == 200
    assert r.headers["x-lang"] == "en"
    assert engine.calls[-1] == ("Hello world", "en")

    r = client.post("/synthesise", json={"text": "नमस्ते", "lang": "hi"})
    assert r.status_code == 200
    assert r.headers["x-lang"] == "hi"
    assert engine.calls[-1] == ("नमस्ते", "hi")


def test_synthesise_rejects_bad_lang_pattern(client: TestClient) -> None:
    # Pydantic pattern validation → 422 (not routed through to engine).
    r = client.post("/synthesise", json={"text": "hi", "lang": "EN-US"})
    assert r.status_code == 422


def test_synthesise_rejects_empty_text(client: TestClient) -> None:
    # Pydantic catches empty strings at the schema layer → 422.
    response = client.post("/synthesise", json={"text": ""})
    assert response.status_code == 422


def test_synthesise_rejects_whitespace_only(client: TestClient) -> None:
    response = client.post("/synthesise", json={"text": "   "})
    assert response.status_code == 400


def test_synthesise_rejects_over_limit_text(client: TestClient) -> None:
    response = client.post("/synthesise", json={"text": "ନ" * 200})
    assert response.status_code == 413


def test_synthesise_logs_tenant_header(
    client: TestClient, engine: FakeEngine
) -> None:
    # We don't assert on logs here (structlog output is JSON to stderr),
    # but the request should still succeed when the gateway-injected
    # tenant headers are present.
    response = client.post(
        "/synthesise",
        json={"text": "ନମସ୍କାର"},
        headers={"X-Tenant-Slug": "utkal-university"},
    )
    assert response.status_code == 200
    assert len(engine.calls) == 1
