"""Shared pytest fixtures for the gateway test suite."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.tenants import InMemoryTenantRepository, Tenant

# Deliberately fixed for reproducibility in tests.
VALID_TEST_KEY = "aaas_live_" + "a" * 32
REVOKED_TEST_KEY = "aaas_live_" + "b" * 32
UNKNOWN_TEST_KEY = "aaas_live_" + "c" * 32
OPERATOR_TEST_KEY = "aaas_live_" + "d" * 32

OPERATOR_TENANT = Tenant(
    id=UUID("00000000-0000-0000-0000-000000000001"),
    slug="utkal-university",
    display_name="Utkal University",
    category="university",
    region="IN-OD",
)

TEST_TENANT = Tenant(
    id=UUID("00000000-0000-0000-0000-000000000042"),
    slug="test-tenant",
    display_name="Test Tenant",
    category="university",
    region="IN-OD",
)


@pytest.fixture
def settings() -> Settings:
    """Isolated settings — tests never read the real `.env`."""
    return Settings(
        aaas_env="test",
        log_level="WARNING",
        database_url="postgresql://test:test@localhost/test",
        redis_url="redis://localhost:6379/15",
    )


@pytest.fixture
def tenant_repository() -> InMemoryTenantRepository:
    """A fresh repo per test, seeded with one active and one revoked key."""
    repo = InMemoryTenantRepository()
    repo.add(TEST_TENANT, raw_key=VALID_TEST_KEY, name="test-active")
    repo.add(OPERATOR_TENANT, raw_key=OPERATOR_TEST_KEY, name="test-operator")
    revoked = repo.add(TEST_TENANT, raw_key=REVOKED_TEST_KEY, name="test-revoked")
    # Replace the revoked entry with one that has revoked_at set.
    from dataclasses import replace
    from datetime import datetime

    repo.keys_by_hash[revoked.key_hash] = replace(
        revoked, revoked_at=datetime.now(UTC)
    )
    return repo


@pytest.fixture
def app(
    settings: Settings, tenant_repository: InMemoryTenantRepository
) -> FastAPI:
    return create_app(settings=settings, tenant_repository=tenant_repository)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """Use as a context manager so the app's lifespan fires
    (sets up `app.state.http_client` etc.)."""
    with TestClient(app) as c:
        yield c
