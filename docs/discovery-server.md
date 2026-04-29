# Discovery Server — Hosting Guide

The discovery server is an optional component that lets users publish their passkey-derived symbol identity so others can look them up. Multiple servers can run independently without symbol collisions, and they can be merged into a single database at any time.

Two deployment options:

| Option | Stack | Cost | Best for |
|--------|-------|------|----------|
| **Cloudflare Worker** | Worker + D1 (SQLite) | Free tier | PRYSYM-hosted registry, quick personal instances |
| **Docker Compose**   | FastAPI + PostgreSQL  | VPS/cloud  | Full control, custom auth, high write volume |

Both implement the same REST API — the PWA works with either.

---

## Option 1 — Cloudflare Worker (Recommended, Zero Cost)

The `worker/` directory contains a Cloudflare Worker that runs the complete discovery API on Cloudflare's free tier.

**Free tier limits:** 100k requests/day · 5M D1 reads/day · 100k writes/day · 5GB storage

### Deploy

```bash
# Prerequisites: Cloudflare account, wrangler CLI, wrangler login
cd worker
npm install
wrangler d1 create ois-discovery    # → copy database_id into wrangler.toml
wrangler d1 execute ois-discovery --file=schema.sql
wrangler secret put WEBAUTHN_VERIFY_ORIGIN   # → true
wrangler secret put ALLOWED_ORIGINS          # → https://PRYSYM.github.io,http://localhost:8080
wrangler deploy
```

See [../worker/README.md](../worker/README.md) for the full step-by-step guide.

### Local dev

```bash
wrangler dev --local
wrangler d1 execute ois-discovery --local --file=schema.sql
# → http://localhost:8787
```

---

## Option 2 — Docker Compose (Self-Hosted)

### Quick Start

The repository ships a `docker-compose.yml` that starts PostgreSQL and the discovery server with a single command.

```bash
git clone https://github.com/PRYSYM/open-identity-symbols
cd open-identity-symbols
docker compose up -d
```

Services started:

| Service | Port | URL |
|---------|------|-----|
| Discovery Server | 8001 | http://localhost:8001/docs |
| PostgreSQL | 5432 | — |

Tables are created automatically on first startup via SQLAlchemy `create_all`.

---

## Running the Discovery Server Standalone

If you only want the discovery server without the full stack:

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ (or use the Docker Compose postgres service)

### Install

```bash
# From repo root
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r discovery/requirements.txt
```

### Configure

Set environment variables (or create a `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://ois_user:ois_pass@localhost:5432/ois_discovery` | PostgreSQL connection string |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins, or `*` for all |
| `WEBAUTHN_VERIFY_ORIGIN` | `true` | Set `false` only in local dev without HTTPS |
| `CHALLENGE_TTL_SECONDS` | `300` | How long a challenge token is valid (seconds) |

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/ois_discovery"
export CORS_ORIGINS="https://my-pwa.example.com"
```

### Create the Database

```bash
# Create the database (if it doesn't exist yet)
createdb -U postgres ois_discovery

# Tables are created automatically on server startup via SQLAlchemy create_all
```

### Run

```bash
uvicorn discovery.main:app --host 0.0.0.0 --port 8001 --reload
```

Open http://localhost:8001/docs to verify it's running.

---

## Connecting the PWA to Your Server

Open the PWA in a browser, click **Server Config** (shown after your identity is generated), and enter your discovery server URL:

```
https://discovery.example.com
```

The PWA saves this URL in `localStorage` (`ois_server_url_v1`) and uses it for all publish/search operations.

---

## Running in Production

### Reverse Proxy (Nginx example)

```nginx
server {
    listen 443 ssl;
    server_name discovery.example.com;

    ssl_certificate     /etc/letsencrypt/live/discovery.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/discovery.example.com/privkey.pem;

    location / {
        proxy_pass         http://127.0.0.1:8001;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-Proto https;
    }
}
```

### Systemd Service

```ini
[Unit]
Description=OIS Discovery Server
After=network.target postgresql.service

[Service]
User=ois
WorkingDirectory=/opt/open-identity-symbols
EnvironmentFile=/opt/open-identity-symbols/.env
ExecStart=/opt/open-identity-symbols/.venv/bin/uvicorn discovery.main:app --host 127.0.0.1 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target
```

### Environment Recommendations for Production

```bash
DATABASE_URL=postgresql://ois_user:strongpass@localhost:5432/ois_discovery
CORS_ORIGINS=https://my-pwa.example.com,https://other-trusted-pwa.com
WEBAUTHN_VERIFY_ORIGIN=true
CHALLENGE_TTL_SECONDS=300
```

Set `CORS_ORIGINS` to a specific list of your PWA origins instead of `*` to prevent unauthorized clients from publishing to your server.

---

## Running Tests

```bash
# From repo root, with venv active
PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest discovery/tests/ -v  # Windows
PYTHONUTF8=1 python -m pytest discovery/tests/ -v                    # Linux/Mac
```

Tests use an in-memory SQLite database (StaticPool) — no PostgreSQL required. All 33 tests should pass.

---

## Federation and Merging

### How No-Collision Is Guaranteed

Symbol triples are derived deterministically from the passkey's SPKI (public key bytes) via SHA-256. Since each passkey's key material is unique by construction (P-256 key generation uses CSPRNG), two distinct users will never produce the same SPKI, and therefore never the same symbol triple.

The probability of two independent users accidentally deriving the same triple across different servers is approximately **1 in 156 billion** (5390³ combinations with distinct-index constraint).

### Global Merge Key

Every published identity has:

```
public_key_id = SHA-256(SPKI bytes)   # stored as 64 hex chars
```

This value is the same on every server that has seen the same user, making it a stable cross-server primary key.

### Merging Two Servers

To merge the database of Server B into Server A:

**Step 1 — Export Server B**

```bash
pg_dump -h serverb-host -U ois_user -t identities -F c ois_discovery > server_b.dump
```

**Step 2 — Restore to a staging table on Server A**

```bash
# Create a temporary staging table
psql -U ois_user -d ois_discovery -c "CREATE TABLE identities_b (LIKE identities INCLUDING ALL);"

# Restore into it (adjust the table name via --table flag or post-process)
pg_restore -U ois_user -d ois_discovery server_b.dump  # then rename as needed
```

**Step 3 — Merge with conflict handling**

```sql
-- Insert rows from Server B; skip if public key already known
INSERT INTO identities (
    public_key_id, symbol_id, alias, public_key_spki,
    origin, public_profile, published_at, updated_at
)
SELECT
    public_key_id, symbol_id, alias, public_key_spki,
    origin, public_profile, published_at, updated_at
FROM identities_b
ON CONFLICT (public_key_id) DO NOTHING;

-- Detect symbol_id or alias collisions from truly different keys
SELECT b.*
FROM identities_b b
LEFT JOIN identities a ON a.public_key_id = b.public_key_id
WHERE a.public_key_id IS NULL
  AND (
      EXISTS (SELECT 1 FROM identities x WHERE x.symbol_id = b.symbol_id)
   OR EXISTS (SELECT 1 FROM identities x WHERE x.alias     = b.alias)
  );
```

Rows returned by the collision query represent the (extremely rare) case where two users on different servers derived the same triple from different keys. These rows require manual operator review — the user on the merged server keeps their triple; the colliding user gets a newly generated one.

**Step 4 — Clean up**

```sql
DROP TABLE identities_b;
```

### Summary: What Makes Identities Portable

| Property | Value |
|----------|-------|
| Globally unique ID | `public_key_id` (SHA-256 of SPKI, hex) |
| Human ID (per-server unique) | `symbol_id` (3 emojis) |
| Human alias (per-server unique) | `alias` (3 words) |
| Ownership proof | WebAuthn assertion — only the hardware key can sign |
| Merge strategy | `INSERT … ON CONFLICT (public_key_id) DO NOTHING` |
