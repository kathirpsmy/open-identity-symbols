# Architecture

## Overview

OIS has two components:

| Component | Role | Deployment |
|-----------|------|------------|
| **PWA** | Identity generation, credential storage, offline use | GitHub Pages (static) |
| **Discovery Server** | Optional public registry for symbol lookup | Self-hosted / Docker |

The PWA works entirely without the discovery server. Discovery is opt-in — users publish their identity only if they want to be findable.

---

## PWA — Client-side Identity

```
Browser
  └── pwa/
       ├── index.html        Entry point
       ├── app.js            WebAuthn, derivation, IndexedDB, discovery calls
       ├── sw.js             Service worker (offline, cache-first)
       ├── manifest.json     PWA manifest
       └── data/
            ├── pool.js      5,390 Unicode symbols (auto-generated)
            └── alias.js     Matching English-word aliases (auto-generated)
```

### Identity Generation Flow

```
User taps "Generate"
  │
  ├─ navigator.credentials.create()   ← WebAuthn API
  │    │  (OS prompts: Touch ID / Face ID / PIN)
  │    └─ Credential { publicKey: CryptoKey }
  │
  ├─ exportKey("spki", publicKey)      ← SPKI DER bytes
  │
  ├─ SHA-256(spki_bytes)               ← 32-byte digest
  │    │
  │    ├─ idx_a = uint32_be(digest, 0) % POOL_SIZE
  │    ├─ idx_b = uint32_be(digest, 4) % POOL_SIZE
  │    └─ idx_c = uint32_be(digest, 8) % POOL_SIZE
  │
  └─ symbol_id = POOL[a] + "-" + POOL[b] + "-" + POOL[c]
     alias     = ALIAS[a] + "-" + ALIAS[b] + "-" + ALIAS[c]
```

If any two indices are equal (collision), the window shifts by 3 bytes and indices are re-derived from offsets 3, 6, 9.

### Symbol Derivation Algorithm

```
digest = SHA-256(SPKI DER bytes of P-256 public key)

idx_a = big-endian uint32 at digest[0:4]  mod pool_size
idx_b = big-endian uint32 at digest[4:8]  mod pool_size
idx_c = big-endian uint32 at digest[8:12] mod pool_size

if any two indices are equal:
    idx_a = big-endian uint32 at digest[3:7]  mod pool_size
    idx_b = big-endian uint32 at digest[6:10] mod pool_size
    idx_c = big-endian uint32 at digest[9:13] mod pool_size

symbol_id = pool[idx_a] + "-" + pool[idx_b] + "-" + pool[idx_c]
alias     = alias[idx_a] + "-" + alias[idx_b] + "-" + alias[idx_c]
```

The algorithm is identical in JavaScript (`pwa/app.js`) and Python (`discovery/services/symbol_derive.py`), enabling server-side verification of client-generated identities.

### Data Files

`pwa/data/pool.js` and `pwa/data/alias.js` are auto-generated at CI time from the Python source in `data/`. The generation script is `pwa/scripts/export_data.py`.

---

## Discovery Server — Optional Registry

```
discovery/
├── main.py           FastAPI application (port 8001)
├── config.py         Settings (DATABASE_URL, CORS_ORIGINS, WEBAUTHN_VERIFY)
├── database.py       SQLAlchemy / PostgreSQL
├── models.py         SymbolEntry model
├── schemas.py        Pydantic request/response schemas
├── api/
│   ├── challenge.py  GET  /challenge              → WebAuthn challenge
│   ├── publish.py    POST /publish                → Register identity
│   ├── lookup.py     GET  /lookup/{symbol_id}     → Fetch public metadata
│   └── search.py     GET  /search?q=...           → Full-text search
└── services/
    ├── symbol_derive.py    Server-side derivation (matches PWA algorithm)
    └── webauthn_verify.py  Verify WebAuthn assertions
```

### Database Schema

```sql
CREATE TABLE symbol_entries (
    id          SERIAL PRIMARY KEY,
    symbol_id   TEXT UNIQUE NOT NULL,   -- e.g. "⚙-🌊-🔥"
    alias       TEXT NOT NULL,          -- e.g. "gear-wave-fire"
    public_key  BYTEA NOT NULL,         -- SPKI DER bytes of P-256 public key
    proof       JSONB NOT NULL,         -- WebAuthn assertion used at publish time
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

### Publish Flow

```
Client                            Discovery Server
  │                                     │
  ├─ GET /challenge              ──────►│  returns random hex challenge
  │                                     │
  ├─ navigator.credentials.get()        │  (client signs challenge with passkey)
  │    └─ assertion { signature, ... }  │
  │                                     │
  ├─ POST /publish { symbol_id,  ──────►│  1. verify WebAuthn assertion
  │      alias, public_key, proof }     │  2. re-derive symbol_id from public_key
  │                                     │  3. confirm match
  │                                     │  4. store entry
  │◄─────────────────────────────────── │  201 Created
```

The server re-derives the symbol ID from the submitted public key and rejects the request if it does not match. This makes it impossible to publish a symbol ID you do not own.

---

## Symbol Pool

- **Source:** `data/unicode_pool.py`
- **Size:** ~5,390 symbols
- **Exclusions:** religious, political, national flags, gendered symbols, human faces
- **Capacity:** 5390³ ≈ 156 billion unique combinations

See [specs/unicode-pool.md](../specs/unicode-pool.md) for full curation rules.

---

## Deployment

### PWA

Deployed automatically to GitHub Pages on every push to `main` that touches `pwa/**`, `data/**`, or `docs/**`. The workflow builds a combined site:

- `/` → landing page (`docs/index.html`)
- `/app/` → PWA files

### Discovery Server

```bash
docker compose up   # starts postgres + discovery server
```

See [discovery-server.md](./discovery-server.md) for configuration and API reference.
