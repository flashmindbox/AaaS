"""Runtime configuration loaded from env vars (see `.env.example`)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All gateway config in one place.

    Values are read from environment variables; a `.env` file is honoured in
    dev but MUST NOT exist in production — secrets come from the secret
    manager (Vault / AWS SM / GCP SM) via real env vars.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    aaas_env: str = Field(default="dev", description="dev | staging | prod")
    log_level: str = Field(default="INFO")
    gateway_port: int = Field(default=8000)

    upstream_tts_url: str = Field(default="http://localhost:8001")
    upstream_stt_url: str = Field(default="http://localhost:8002")
    upstream_translate_url: str = Field(default="http://localhost:8003")
    # Upstream admin endpoints are handled in-gateway now (see
    # app.routes.admin_api), so this URL is vestigial but retained for
    # future split-out without a breaking config change.
    upstream_admin_url: str = Field(default="http://localhost:8004")

    database_url: str = Field(
        default="postgresql://aaas:change-me-in-dev@localhost:5432/aaas"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    oidc_issuer: str = Field(default="http://localhost:8080/realms/aaas")
    oidc_audience: str = Field(default="aaas-gateway")
    oidc_jwks_url: str = Field(
        default="http://localhost:8080/realms/aaas/protocol/openid-connect/certs"
    )

    # Key shipped inside the public browser extension. It is readable by
    # anyone who unzips the extension, so it belongs to its own ordinary
    # (non-operator) tenant and can be rotated by changing this env var.
    # Empty = no extension tenant is seeded.
    extension_api_key: str = Field(default="")

    rate_limit_per_minute: int = Field(default=60)
    rate_limit_burst: int = Field(default=10)

    @property
    def is_prod(self) -> bool:
        return self.aaas_env == "prod"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Memoised so Pydantic doesn't re-read env on every request."""
    return Settings()
