"""End-to-end tests for the `X-API-Key` auth path."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import REVOKED_TEST_KEY, UNKNOWN_TEST_KEY, VALID_TEST_KEY


def test_whoami_requires_api_key_header(client: TestClient) -> None:
    response = client.get("/whoami")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing X-API-Key header"
    assert response.headers["WWW-Authenticate"] == "ApiKey"


def test_whoami_rejects_unknown_key(client: TestClient) -> None:
    response = client.get("/whoami", headers={"X-API-Key": UNKNOWN_TEST_KEY})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or revoked API key"


def test_whoami_rejects_malformed_key(client: TestClient) -> None:
    response = client.get("/whoami", headers={"X-API-Key": "junk"})
    assert response.status_code == 401


def test_whoami_rejects_revoked_key(client: TestClient) -> None:
    response = client.get("/whoami", headers={"X-API-Key": REVOKED_TEST_KEY})
    assert response.status_code == 401


def test_whoami_returns_tenant_for_valid_key(client: TestClient) -> None:
    response = client.get("/whoami", headers={"X-API-Key": VALID_TEST_KEY})
    assert response.status_code == 200
    body = response.json()
    assert body["tenant_slug"] == "test-tenant"
    assert body["tenant_region"] == "IN-OD"
    assert "tts.read" in body["scopes"]


def test_health_endpoint_is_not_auth_gated(client: TestClient) -> None:
    """Liveness must not require auth — Kubernetes probes won't send headers."""
    response = client.get("/healthz")
    assert response.status_code == 200
