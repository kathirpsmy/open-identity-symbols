# Architecture

## System Overview

```
Browser
  │
  ▼
[React + Vite]  ──────────────────── Nginx (port 80)
                                           │ /api/*
                                           ▼
                              [FastAPI Backend] (port 8000)
                              │               │
                              ▼               ▼
                         [PostgreSQL]      [Redis]
```

## Backend

### Layers

| Layer | Path | Responsibility |
|-------|------|----------------|
| API Routes | `backend/api/routes/` | HTTP handling, validation, response shaping |
| Services | `backend/services/` | Business logic (identity engine) |
| Models | `backend/models/` | SQLAlchemy ORM models |
| Schemas | `backend/schemas/` | Pydantic I/O schemas |
| Core | `backend/core/` | Config, DB session, security primitives |
| Data | `backend/data/` | Unicode pool + alias map (pure Python, no DB) |

### Identity Engine Flow

```
Request → identity_engine.generate_symbol_id()
            │
            ├─ Pick 3 distinct symbols from SYMBOL_POOL (5390 items)
            │   using secrets.SystemRandom for CSPRNG
            │
            ├─ Look up alias for each symbol from alias_map
            │
            ├─ Return { symbol_id: "A-B-C", alias: "word1-word2-word3" }
            │
            └─ Caller retries up to 10× on DB uniqueness collision
```

### Auth Flow

```
Register:  POST /register → create User (unconfirmed) → return TOTP QR
Confirm:   POST /confirm-totp (Bearer token) → verify TOTP → mark confirmed
Login:     POST /login → verify password + TOTP → return JWT
```

## Database Schema

```sql
users
  id            INTEGER PK
  email         VARCHAR(254) UNIQUE
  password_hash VARCHAR(255)
  totp_secret   VARCHAR(64)
  totp_confirmed BOOLEAN
  is_active     BOOLEAN
  created_at    TIMESTAMPTZ

identities
  id         INTEGER PK
  user_id    INTEGER FK → users.id UNIQUE
  symbol_id  VARCHAR(64) UNIQUE
  alias      VARCHAR(128) UNIQUE
  created_at TIMESTAMPTZ

profiles
  id         INTEGER PK
  user_id    INTEGER FK → users.id UNIQUE
  data       JSONB      -- { display_name, bio, location, ... }
  visibility JSONB      -- { field: "public"|"private" }
  updated_at TIMESTAMPTZ
```

## Security

- Passwords: bcrypt (cost factor 12)
- Sessions: HS256 JWT, configurable TTL
- 2FA: RFC 6238 TOTP, ±1 window
- CORS: configurable origin allowlist
- No sensitive data in JWT payload (only email as `sub`)

---

## Target Architecture (v2 — Distributed)

The v2 design removes the server as a required participant in identity creation. The backend becomes an optional discovery service.

### System Overview

```
Human Identity Flow
─────────────────────────────────────────────────────────────
Mobile PWA  (static site — GitHub Pages or any CDN)
  │
  ├─ navigator.credentials.create()
  │    Private key → device secure enclave
  │    Syncs automatically: iCloud Keychain (iOS/macOS)
  │                         Google Password Manager (Android/Chrome)
  │
  ├─ SHA-256(credentialPublicKey) → 3 symbol indices → ⚙-🌊-🔥
  │
  ├─ Identity is live. No server needed.
  │
  └─ Optional: POST /publish → discovery server
       {symbol_id, public_key_jwk, alias, public_profile}

Entity Identity Flow
─────────────────────────────────────────────────────────────
CLI / server SDK
  │
  ├─ Generate Ed25519 keypair (private key stays on server)
  └─ Same derivation: SHA-256(publicKey) → 3 symbols

Optional Discovery Server  (self-hostable)
─────────────────────────────────────────────────────────────
Stores: symbol_id → { public_key_jwk, alias, public_profile }
No passwords. No email. No session required for lookup.
Publish authenticated by WebAuthn assertion (proof-of-key).
Anyone can run one. PWA is configurable to point to any server.
```

### Symbol Derivation Algorithm

The same algorithm is used for humans (WebAuthn credential key) and entities (server-generated Ed25519 key).

```
input:  credential public key bytes (COSE/DER/raw format)
        pool_size = 5390  (curated Unicode symbol pool)

digest = SHA-256(publicKeyBytes)

idx_a  = big_endian_uint32(digest[0:4])  % pool_size
idx_b  = big_endian_uint32(digest[4:8])  % pool_size
idx_c  = big_endian_uint32(digest[8:12]) % pool_size

# Collision within the triple: shift window by 3 bytes, retry
if idx_a == idx_b or idx_b == idx_c or idx_a == idx_c:
    idx_a = big_endian_uint32(digest[3:7])  % pool_size
    idx_b = big_endian_uint32(digest[6:10]) % pool_size
    idx_c = big_endian_uint32(digest[9:13]) % pool_size

symbol_id = POOL[idx_a] + "-" + POOL[idx_b] + "-" + POOL[idx_c]
alias     = ALIAS[idx_a] + "-" + ALIAS[idx_b] + "-" + ALIAS[idx_c]
```

**Collision probability:** With 5,390³ ≈ 156 billion possible triples and SHA-256 output, the probability of two distinct public keys mapping to the same triple is negligible for any realistic population.

### Ownership Verification (no server required)

```
Verifier receives:
  { symbol_id, public_key_jwk, challenge, signature }

Step 1: Derive expected symbol from public_key_jwk
        → compare to symbol_id (must match)

Step 2: Verify WebAuthn assertion:
        signature = sign(authenticatorData || SHA-256(clientDataJSON))
        using public_key_jwk

If both pass → claimant controls the private key → identity is authentic.
```

### Human vs. Entity Distinction

| Attribute | Human (WebAuthn passkey) | Entity (server keypair) |
|-----------|--------------------------|-------------------------|
| Key origin | Device secure enclave | Server-generated |
| Credential type | `public-key` (WebAuthn) | Raw Ed25519/RSA |
| User-presence flag | `UP=1, UV=1` in authenticatorData | Absent |
| Generation tool | PWA in mobile browser | CLI / server SDK |
| Key recovery | iCloud / Google Keychain sync | Operator's key management |

### Discovery Server Schema (v2)

```sql
symbols
  symbol_id    VARCHAR(64) PRIMARY KEY
  alias        VARCHAR(128) UNIQUE
  public_key   JSONB        -- JWK format
  public_profile JSONB      -- optional, user-controlled
  published_at TIMESTAMPTZ
```

No `users`, `passwords`, `sessions`, or `totp` tables needed for the discovery server role.
