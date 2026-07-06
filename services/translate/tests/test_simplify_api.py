"""Smoke tests for the /simplify HTTP surface (Easy Read).

Same wiring as test_translate_api.py: app factory + deterministic
engines, no network. Guards the response shape the widget depends on.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.engine.mock import MockTranslateEngine
from app.main import create_app

BUREAUCRATIC_EN = (
    "Applicants shall furnish the requisite documents prior to the "
    "stipulated date w.e.f. 01.01.2026."
)


@pytest.fixture()
def client() -> TestClient:
    app = create_app(
        settings=Settings(engine="mock"), engine=MockTranslateEngine()
    )
    with TestClient(app) as c:
        yield c


def test_simplify_plain_english(client: TestClient) -> None:
    r = client.post("/simplify", json={"text": BUREAUCRATIC_EN, "lang": "en"})
    assert r.status_code == 200
    body = r.json()
    assert body["lang"] == "en"
    assert body["engine"] == "rules"
    text = body["text"]
    assert "give" in text
    assert "required" in text
    assert "before" in text
    assert "with effect from" in text
    assert "furnish" not in text
    assert "requisite" not in text
    assert "stipulated" not in text


def test_simplify_splits_long_odia_sentence(client: TestClient) -> None:
    long_odia = (
        "ସମସ୍ତ ଆବେଦନକାରୀ ନିର୍ଦ୍ଧାରିତ ତାରିଖ ପୂର୍ବରୁ ଆବଶ୍ୟକୀୟ କାଗଜପତ୍ର ଦାଖଲ କରିବେ, "
        "ଏବଂ ଯେଉଁମାନେ ଦାଖଲ କରିପାରିବେ ନାହିଁ ସେମାନଙ୍କ ଆବେଦନ ଅଗ୍ରାହ୍ୟ ହେବ ବୋଲି ଅବଗତ କରାଯାଉଅଛି।"
    )
    r = client.post("/simplify", json={"text": long_odia, "lang": "or"})
    assert r.status_code == 200
    body = r.json()
    text = body["text"]
    # Glossary applied…
    assert "ନିର୍ଦ୍ଧାରିତ" not in text
    assert "ସ୍ଥିର" in text
    # …and the overlong danda sentence was split into more sentences.
    assert text.count("।") >= 2


def test_simplify_odia_with_latin_fragments_stays_odia(client: TestClient) -> None:
    # Regression: translate -> Easy Read injected English words into
    # Odia text ("No." -> "number", "w.e.f." -> "with effect from").
    text = "ବିଜ୍ଞପ୍ତି No. 1247 ଅନୁଯାୟୀ, govt. ଅଫିସ୍ 15.04.2026 w.e.f. ବନ୍ଦ ରହିବ।"
    r = client.post("/simplify", json={"text": text, "lang": "or"})
    assert r.status_code == 200
    out = r.json()["text"]
    assert "number" not in out
    assert "with effect from" not in out
    assert "government" not in out
    assert "No. 1247" in out
    assert "15.04.2026" in out          # dates no longer mangled
    assert "ସରକାର" in out               # govt. expanded in-language


def test_simplify_is_idempotent(client: TestClient) -> None:
    first = client.post("/simplify", json={"text": BUREAUCRATIC_EN, "lang": "en"}).json()["text"]
    second = client.post("/simplify", json={"text": first, "lang": "en"}).json()["text"]
    assert first == second


def test_simplify_unknown_lang_still_splits(client: TestClient) -> None:
    r = client.post("/simplify", json={"text": "One. Two. Three.", "lang": "fr"})
    assert r.status_code == 200
    assert r.json()["text"] == "One. Two. Three."


def test_simplify_rejects_oversize_input(client: TestClient) -> None:
    settings = Settings(engine="mock")
    r = client.post(
        "/simplify",
        json={"text": "x" * (settings.max_input_chars + 1), "lang": "en"},
    )
    assert r.status_code == 413


def test_simplify_rejects_missing_lang(client: TestClient) -> None:
    r = client.post("/simplify", json={"text": "hello"})
    assert r.status_code == 422
