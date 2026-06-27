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


def test_admin_index_references_local_axe(client: TestClient) -> None:
    response = client.get("/admin/")
    assert response.status_code == 200
    body = response.text
    # axe-core must not come from a CDN — the offline demo bundle has
    # no network access, and the rehearsal checklist kills Wi-Fi.
    assert "cdn.jsdelivr.net" not in body, (
        "admin/index.html is loading axe-core from jsDelivr — this "
        "breaks the offline demo path. Point it at ./vendor/axe.min.js."
    )
    assert "vendor/axe.min.js" in body


def test_admin_vendor_axe_is_served(client: TestClient) -> None:
    response = client.get("/admin/vendor/axe.min.js")
    assert response.status_code == 200
    # Deque publishes axe-core with a leading banner — sanity check
    # that we got the real thing, not a 404 page wrapped in HTML.
    assert "axe" in response.text[:400].lower()
    assert "deque" in response.text[:400].lower()
