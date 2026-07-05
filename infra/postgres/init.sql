-- AaaS Postgres init script. Runs once on first container boot.
-- Keep idempotent (CREATE ... IF NOT EXISTS) so re-running is safe.

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";

-- Keycloak shares this server in dev
CREATE USER keycloak WITH PASSWORD 'keycloak';
CREATE DATABASE keycloak OWNER keycloak;
GRANT ALL PRIVILEGES ON DATABASE keycloak TO keycloak;

-- Schemas for AaaS core
CREATE SCHEMA IF NOT EXISTS core       AUTHORIZATION aaas;
CREATE SCHEMA IF NOT EXISTS tenant     AUTHORIZATION aaas;
CREATE SCHEMA IF NOT EXISTS audit      AUTHORIZATION aaas;
CREATE SCHEMA IF NOT EXISTS consent    AUTHORIZATION aaas;

-- ---------------------------------------------------------------
-- tenants: one row per institution that plugs in
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenant.tenants (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  slug            CITEXT NOT NULL UNIQUE,
  display_name    TEXT NOT NULL,
  category        TEXT NOT NULL CHECK (
    category IN ('school','university','exam-board','ministry','municipality','other')
  ),
  region          TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS tenants_region_idx ON tenant.tenants (region);

-- ---------------------------------------------------------------
-- api_keys: per-tenant credentials
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenant.api_keys (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id       UUID NOT NULL REFERENCES tenant.tenants (id) ON DELETE CASCADE,
  name            TEXT NOT NULL,
  key_hash        TEXT NOT NULL,         -- store only sha256
  key_prefix      TEXT NOT NULL,         -- first 8 chars, for lookup
  scopes          TEXT[] NOT NULL DEFAULT '{}',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_used_at    TIMESTAMPTZ,
  revoked_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS api_keys_tenant_idx ON tenant.api_keys (tenant_id);
CREATE INDEX IF NOT EXISTS api_keys_prefix_idx ON tenant.api_keys (key_prefix);

-- ---------------------------------------------------------------
-- audit log — append only, every mutating call lands here
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit.events (
  id              BIGSERIAL PRIMARY KEY,
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  actor           TEXT,                  -- tenant slug, user id, or system
  action          TEXT NOT NULL,
  resource        TEXT,
  resource_id     TEXT,
  ip              INET,
  user_agent      TEXT,
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS audit_events_occurred_idx ON audit.events (occurred_at DESC);
CREATE INDEX IF NOT EXISTS audit_events_actor_idx    ON audit.events (actor);

-- Prevent UPDATE/DELETE on audit events (append-only).
CREATE OR REPLACE FUNCTION audit.reject_mutations() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'audit.events is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_events_no_update ON audit.events;
CREATE TRIGGER audit_events_no_update
  BEFORE UPDATE OR DELETE ON audit.events
  FOR EACH ROW EXECUTE FUNCTION audit.reject_mutations();

-- ---------------------------------------------------------------
-- consent records — DPDP Act compliance
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS consent.records (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  subject_hash    TEXT NOT NULL,         -- never store raw PII as the subject id
  tenant_id       UUID REFERENCES tenant.tenants (id) ON DELETE SET NULL,
  purpose         TEXT NOT NULL,         -- e.g. 'speech-to-text', 'model-improvement'
  given_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  withdrawn_at    TIMESTAMPTZ,
  policy_version  TEXT NOT NULL,
  evidence        JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS consent_subject_idx ON consent.records (subject_hash);

COMMENT ON TABLE consent.records IS
  'DPDP Act 2023 evidence of notice+consent. Subject ids are hashed so consent records never become PII themselves.';

-- ---------------------------------------------------------------
-- seed: a sample tenant for local dev
-- ---------------------------------------------------------------
INSERT INTO tenant.tenants (slug, display_name, category, region)
VALUES ('demo-university', 'Demo University', 'university', 'IN-WB')
ON CONFLICT (slug) DO NOTHING;
