"""Regression tests for the gateway's static mounts.

If someone switches `_mount_demo_assets` to serve `apps/widget/src/widget.js`
by accident, the shipped widget would contain the literal placeholder
`__AAAS_NOTO_ORIYA_B64__` instead of the inlined font bytes — Odia
conjuncts would silently fall back to the system font on laptops that
don't have Noto Sans Oriya installed. Catch that in CI.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_widget_js_is_served(client: TestClient) -> None:
    response = client.get("/widget.js")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/javascript")


def test_widget_js_has_inlined_font_not_placeholder(client: TestClient) -> None:
    response = client.get("/widget.js")
    body = response.text
    assert "__AAAS_NOTO_ORIYA_B64__" not in body, (
        "gateway is serving the unbuilt src/widget.js — run "
        "`python scripts/build_widget.py` and confirm the mount points "
        "at apps/widget/dist/widget.js."
    )
    assert "@font-face" in body
    assert "Noto Sans Oriya" in body
    assert "data:font/woff2;base64" in body


def test_admin_console_is_served_and_offline_safe(client: TestClient) -> None:
    response = client.get("/admin/")
    assert response.status_code == 200
    body = response.text
    # The console must not pull anything from a CDN — the offline demo
    # bundle has no network access, and the rehearsal checklist kills
    # Wi-Fi. Everything it needs is same-origin.
    assert "cdn." not in body
    assert "googleapis" not in body
    assert "admin.js" in body
    assert "Operator Console" in body


def test_admin_console_js_is_served(client: TestClient) -> None:
    response = client.get("/admin/admin.js")
    assert response.status_code == 200
    # It drives the live dashboard off the in-gateway admin API.
    assert "/admin/api/usage" in response.text
