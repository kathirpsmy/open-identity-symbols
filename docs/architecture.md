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
