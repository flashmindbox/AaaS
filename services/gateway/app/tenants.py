"""Tenant and API-key domain model, plus a swappable repository.

Two implementations ship:

- :class:`InMemoryTenantRepository` — used by unit tests and the dev
  fallback when Postgres isn't reachable. Seeded from a static dict.
- :class:`PostgresTenantRepository` — the real thing, lazily connects
  to the pool configured in :mod:`app.db`.

The repository is a Protocol rather than a concrete class so callers
never import the Postgres implementation directly — tests can replace
it wholesale.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

# API keys look like `aaas_live_<32-hex>`. The literal prefix makes the
# token obvious to secret-scanners (GitHub push protection, TruffleHog).
_KEY_PATTERN = re.compile(r"^aaas_live_[0-9a-f]{32}$")
_KEY_LOOKUP_PREFIX_LEN = 14  # len("aaas_live_") + 4 hex chars


class InvalidApiKeyFormatError(ValueError):
    """Raised when an API-key string doesn't match the expected shape."""


@dataclass(frozen=True, slots=True)
class Tenant:
    id: UUID
    slug: str
    display_name: str
    category: str
    region: str | None = None


@dataclass(frozen=True, slots=True)
class ApiKey:
    id: UUID
    tenant_id: UUID
    name: str
    key_prefix: str
    key_hash: str
    scopes: tuple[str, ...]
    revoked_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


def hash_api_key(raw_key: str) -> str:
    """SHA-256 of the raw key. We never store raw keys."""
    if not _KEY_PATTERN.fullmatch(raw_key):
        raise InvalidApiKeyFormatError(
            "API key must match aaas_live_<32-hex-chars>"
        )
    return hashlib.sha256(raw_key.encode("ascii")).hexdigest()


def key_prefix(raw_key: str) -> str:
    """First 14 chars — indexed in Postgres for O(log n) lookup."""
    if len(raw_key) < _KEY_LOOKUP_PREFIX_LEN:
        raise InvalidApiKeyFormatError("key too short")
    return raw_key[:_KEY_LOOKUP_PREFIX_LEN]


def mint_api_key() -> str:
    """Generate a new `aaas_live_...` key. Only the raw value is returned;
    callers MUST store only the hash."""
    return f"aaas_live_{secrets.token_hex(16)}"


class TenantRepository(Protocol):
    """Read-only access the gateway needs; writes live in admin-api."""

    async def find_tenant_by_api_key(
        self, raw_key: str
    ) -> tuple[Tenant, ApiKey] | None:
        """Return (tenant, key) if the raw key is valid, active, and known."""


@dataclass
class InMemoryTenantRepository:
    """Seeded from a dict. Not thread-safe — tests only."""

    tenants: dict[UUID, Tenant] = field(default_factory=dict)
    keys_by_hash: dict[str, ApiKey] = field(default_factory=dict)

    async def find_tenant_by_api_key(
        self, raw_key: str
    ) -> tuple[Tenant, ApiKey] | None:
        try:
            h = hash_api_key(raw_key)
        except InvalidApiKeyFormatError:
            return None
        key = self.keys_by_hash.get(h)
        if key is None or not key.is_active:
            return None
        tenant = self.tenants.get(key.tenant_id)
        if tenant is None:
            return None
        return tenant, key

    def add(self, tenant: Tenant, raw_key: str, *, name: str = "dev") -> ApiKey:
        """Convenience: register a tenant + key for tests/dev seeding."""
        api_key = ApiKey(
            id=uuid4(),
            tenant_id=tenant.id,
            name=name,
            key_prefix=key_prefix(raw_key),
            key_hash=hash_api_key(raw_key),
            scopes=("tts.read", "stt.read"),
        )
        self.tenants[tenant.id] = tenant
        self.keys_by_hash[api_key.key_hash] = api_key
        return api_key
