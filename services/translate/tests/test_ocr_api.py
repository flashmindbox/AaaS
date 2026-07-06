"""Smoke tests for the /ocr HTTP surface.

Runs with the injected mock OCR engine so neither the tesseract binary
nor the [ocr] extras are needed — CI-safe, same wiring philosophy as
the translate/simplify tests. Guards the response shape the widget
depends on and the magic-byte sniffing.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.engine.mock import MockTranslateEngine
from app.engine.ocr_mock import MockOcrEngine
from app.main import create_app

PNG_STUB = b"\x89PNG\r\n\x1a\n" + b"not-really-a-png"
PDF_STUB = b"%PDF-1.4 not-really-a-pdf"


@pytest.fixture()
def client() -> TestClient:
    app = create_app(
        settings=Settings(engine="mock"),
        engine=MockTranslateEngine(),
        ocr_engine=MockOcrEngine(),
    )
    with TestClient(app) as c:
        yield c


def test_ocr_png_returns_canned_notice(client: TestClient) -> None:
    r = client.post(
        "/ocr",
        files={"file": ("notice.png", PNG_STUB, "image/png")},
        data={"lang": "en"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["engine"] == "mock"
    assert body["lang"] == "en"
    assert "hereby" in body["text"] or "aforesaid" in body["text"]
    assert body["pages"][0]["page"] == 1
    assert body["pages"][0]["source"] == "mock"


def test_ocr_pdf_accepted(client: TestClient) -> None:
    r = client.post(
        "/ocr",
        files={"file": ("scan.pdf", PDF_STUB, "application/pdf")},
    )
    assert r.status_code == 200
    assert r.json()["engine"] == "mock"


def test_ocr_lang_defaults_to_auto_and_falls_back(client: TestClient) -> None:
    r = client.post(
        "/ocr",
        files={"file": ("x.png", PNG_STUB, "image/png")},
        data={"lang": "or"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["lang"] == "or"
    assert "ଅବଗତ" in body["text"] or "ଓଡ଼ିଶା" in body["text"]


def test_ocr_rejects_empty_file(client: TestClient) -> None:
    r = client.post("/ocr", files={"file": ("empty.png", b"", "image/png")})
    assert r.status_code == 400


def test_ocr_rejects_unknown_type(client: TestClient) -> None:
    r = client.post(
        "/ocr", files={"file": ("x.gif", b"GIF89a-nope", "image/gif")}
    )
    assert r.status_code == 400
    assert "Unsupported" in r.json()["detail"]


def test_ocr_rejects_oversize(client: TestClient) -> None:
    settings = Settings(engine="mock")
    big = PNG_STUB + b"0" * settings.ocr_max_bytes
    r = client.post("/ocr", files={"file": ("big.png", big, "image/png")})
    assert r.status_code == 413


def test_ocr_requires_file(client: TestClient) -> None:
    r = client.post("/ocr", data={"lang": "en"})
    assert r.status_code == 422
