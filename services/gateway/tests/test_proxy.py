"""Tests for the /tts, /stt, /translate upstream proxy routes.

`respx` intercepts httpx calls so we don't need real upstream services.
"""

from __future__ import annotations

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from tests.conftest import VALID_TEST_KEY


@pytest.fixture
def headers() -> dict[str, str]:
    return {"X-API-Key": VALID_TEST_KEY}


def test_proxy_requires_auth(client: TestClient) -> None:
    response = client.get("/tts/voices")
    assert response.status_code == 401


@respx.mock
def test_tts_call_is_forwarded_to_upstream(
    client: TestClient, headers: dict[str, str]
) -> None:
    route = respx.get("http://localhost:8001/voices").mock(
        return_value=httpx.Response(
            200,
            json={"voices": ["or-IN-female-1"]},
            headers={"content-type": "application/json"},
        )
    )
    response = client.get("/tts/voices", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"voices": ["or-IN-female-1"]}
    assert route.called


@respx.mock
def test_api_key_is_stripped_before_forwarding(
    client: TestClient, headers: dict[str, str]
) -> None:
    route = respx.post("http://localhost:8001/synthesise").mock(
        return_value=httpx.Response(200, content=b"fake-audio")
    )
    response = client.post(
        "/tts/synthesise",
        headers={**headers, "Content-Type": "application/json"},
        content='{"text": "ନମସ୍କାର"}'.encode(),
    )
    assert response.status_code == 200

    forwarded = route.calls[-1].request.headers
    # Upstream must NOT see the API key.
    assert "x-api-key" not in {k.lower() for k in forwarded}
    assert "authorization" not in {k.lower() for k in forwarded}


@respx.mock
def test_tenant_headers_are_attached(
    client: TestClient, headers: dict[str, str]
) -> None:
    route = respx.get("http://localhost:8002/status").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    client.get("/stt/status", headers=headers)
    forwarded = route.calls[-1].request.headers
    assert forwarded["x-tenant-slug"] == "test-tenant"
    assert forwarded["x-tenant-region"] == "IN-OD"
    assert forwarded["x-tenant-id"]  # UUID string present


@respx.mock
def test_upstream_unreachable_returns_502(
    client: TestClient, headers: dict[str, str]
) -> None:
    respx.get("http://localhost:8002/status").mock(
        side_effect=httpx.ConnectError("refused")
    )
    response = client.get("/stt/status", headers=headers)
    assert response.status_code == 502
    assert "Upstream unreachable" in response.json()["detail"]


@respx.mock
def test_upstream_timeout_returns_504(
    client: TestClient, headers: dict[str, str]
) -> None:
    respx.post("http://localhost:8001/synthesise").mock(
        side_effect=httpx.ReadTimeout("slow")
    )
    response = client.post(
        "/tts/synthesise",
        headers=headers,
        content=b'{"text": "x"}',
    )
    assert response.status_code == 504


