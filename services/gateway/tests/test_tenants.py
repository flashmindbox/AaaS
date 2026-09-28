"""Unit tests for the tenant domain model and in-memory repository."""

from __future__ import annotations

from datetime import UTC
from uuid import UUID

import pytest

from app.tenants import (
    InMemoryTenantRepository,
    InvalidApiKeyFormatError,
    Tenant,
    hash_api_key,
    key_prefix,
    mint_api_key,
)


def _tenant() -> Tenant:
    return Tenant(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        slug="odisha-demo",
        display_name="Odisha Demo",
        category="university",
        region="IN-OD",
    )


class TestKeyFormat:
    def test_valid_key_hashes_deterministically(self) -> None:
        key = "aaas_live_" + "f" * 32
        assert hash_api_key(key) == hash_api_key(key)
        assert len(hash_api_key(key)) == 64  # SHA-256 hex length

    def test_invalid_format_rejected(self) -> None:
        with pytest.raises(InvalidApiKeyFormatError):
            hash_api_key("not-a-key")
        with pytest.raises(InvalidApiKeyFormatError):
            hash_api_key("aaas_live_XYZ")  # non-hex suffix

    def test_key_prefix_is_14_chars(self) -> None:
        key = mint_api_key()
        assert key.startswith("aaas_live_")
        assert len(key_prefix(key)) == 14

    def test_minted_keys_are_unique(self) -> None:
        assert mint_api_key() != mint_api_key()


class TestInMemoryRepository:
    async def test_valid_key_returns_tenant(self) -> None:
        repo = InMemoryTenantRepository()
        t = _tenant()
        key = "aaas_live_" + "1" * 32
        repo.add(t, raw_key=key)
        result = await repo.find_tenant_by_api_key(key)
        assert result is not None
        assert result[0].slug == "odisha-demo"

    async def test_unknown_key_returns_none(self) -> None:
        repo = InMemoryTenantRepository()
        assert await repo.find_tenant_by_api_key("aaas_live_" + "9" * 32) is None

    async def test_malformed_key_returns_none_not_raises(self) -> None:
        repo = InMemoryTenantRepository()
        # Middleware treats bad format as 'not found' → 401, not 500.
        assert await repo.find_tenant_by_api_key("garbage") is None

    async def test_revoked_key_returns_none(self) -> None:
        from dataclasses import replace
        from datetime import datetime

        repo = InMemoryTenantRepository()
        t = _tenant()
        key = "aaas_live_" + "2" * 32
        api_key = repo.add(t, raw_key=key)
        repo.keys_by_hash[api_key.key_hash] = replace(
            api_key, revoked_at=datetime.now(UTC)
        )
        assert await repo.find_tenant_by_api_key(key) is None


class TestCreateTenantEndpoint:
    """POST /admin/api/tenants — the one-call onboarding flow."""

    def test_create_tenant_returns_working_key(self, client) -> None:
        from tests.conftest import OPERATOR_TEST_KEY

        resp = client.post(
            "/admin/api/tenants",
            headers={"X-API-Key": OPERATOR_TEST_KEY},
            json={"display_name": "Berhampur Municipality", "category": "government"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["tenant"]["slug"] == "berhampur-municipality"
        raw = body["raw"]
        assert raw.startswith("aaas_live_")
        # The minted key authenticates immediately.
        who = client.get("/admin/api/tenants", headers={"X-API-Key": raw})
        assert who.status_code == 200
        assert any(t["slug"] == "berhampur-municipality" for t in who.json())

    def test_duplicate_slug_conflicts(self, client) -> None:
        from tests.conftest import OPERATOR_TEST_KEY

        first = client.post(
            "/admin/api/tenants",
            headers={"X-API-Key": OPERATOR_TEST_KEY},
            json={"display_name": "Twin City"},
        )
        assert first.status_code == 201
        dup = client.post(
            "/admin/api/tenants",
            headers={"X-API-Key": OPERATOR_TEST_KEY},
            json={"display_name": "Twin  City"},
        )
        assert dup.status_code == 409


class TestAdminTenantScoping:
    """Only the operator tenant manages other tenants."""

    def test_non_operator_cannot_onboard(self, client) -> None:
        from tests.conftest import VALID_TEST_KEY

        resp = client.post(
            "/admin/api/tenants",
            headers={"X-API-Key": VALID_TEST_KEY},
            json={"display_name": "Rogue Tenant"},
        )
        assert resp.status_code == 403

    def test_non_operator_cannot_mint_for_other_tenant(self, client) -> None:
        from tests.conftest import VALID_TEST_KEY

        resp = client.post(
            "/admin/api/tenants/utkal-university/keys",
            headers={"X-API-Key": VALID_TEST_KEY},
            json={"name": "stolen"},
        )
        assert resp.status_code == 404

    def test_non_operator_can_mint_own_key(self, client) -> None:
        from tests.conftest import VALID_TEST_KEY

        resp = client.post(
            "/admin/api/tenants/test-tenant/keys",
            headers={"X-API-Key": VALID_TEST_KEY},
            json={"name": "rotation"},
        )
        assert resp.status_code == 201

    def test_non_operator_sees_only_itself(self, client) -> None:
        from tests.conftest import VALID_TEST_KEY

        resp = client.get("/admin/api/tenants", headers={"X-API-Key": VALID_TEST_KEY})
        assert [t["slug"] for t in resp.json()] == ["test-tenant"]
        other = client.get(
            "/admin/api/tenants/utkal-university", headers={"X-API-Key": VALID_TEST_KEY}
        )
        assert other.status_code == 404

    def test_operator_sees_all(self, client) -> None:
        from tests.conftest import OPERATOR_TEST_KEY

        resp = client.get("/admin/api/tenants", headers={"X-API-Key": OPERATOR_TEST_KEY})
        assert {t["slug"] for t in resp.json()} >= {"test-tenant", "utkal-university"}
