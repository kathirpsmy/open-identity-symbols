-- OIS Discovery — D1 schema (SQLite)
-- Same schema as SQLAlchemy models in discovery/models.py
-- Run: wrangler d1 execute ois-discovery --file=schema.sql

CREATE TABLE IF NOT EXISTS identities (
  public_key_id   TEXT PRIMARY KEY,            -- SHA-256(SPKI bytes) hex
  symbol_id       TEXT UNIQUE NOT NULL,
  alias           TEXT UNIQUE NOT NULL,
  public_key_spki TEXT NOT NULL,               -- base64url SPKI DER
  credential_id   TEXT,                        -- base64url, for recovery
  origin          TEXT NOT NULL,               -- WebAuthn RP origin
  public_profile  TEXT,                        -- JSON string
  published_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS ix_identities_symbol_id     ON identities(symbol_id);
CREATE INDEX IF NOT EXISTS ix_identities_alias         ON identities(alias);
CREATE INDEX IF NOT EXISTS ix_identities_credential_id ON identities(credential_id);
CREATE INDEX IF NOT EXISTS ix_identities_search        ON identities(symbol_id, alias);

CREATE TABLE IF NOT EXISTS challenges (
  token      TEXT PRIMARY KEY,  -- 64-char hex (32 bytes)
  expires_at TEXT NOT NULL      -- ISO 8601 UTC
);
