"""Liveness and version endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import __version__


def test_healthz_returns_ok(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "gateway"}


def test_version_reports_running_build(client: TestClient) -> None:
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"service": "gateway", "version": __version__}


def test_openapi_docs_mounted(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "AaaS Gateway"
