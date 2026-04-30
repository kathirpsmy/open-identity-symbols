# OIS Discovery — Cloudflare Worker

Cloudflare Worker + D1 implementation of the OIS discovery server.
Same REST API as `discovery/` (FastAPI). Zero hosting cost on the free tier.

Free tier limits: 100k requests/day, 5M D1 reads/day, 100k writes/day, 5GB storage.

---

## Prerequisites

- Cloudflare account (free) — already done
- `wrangler` CLI — already done (`wrangler login` already done)

---

## Deploy (one-time setup)

Run all commands from the `worker/` directory.

### 1. Install dependencies

```bash
cd worker
npm install
```

### 2. Create the D1 database

```bash
wrangler d1 create ois-discovery
```

Copy the `database_id` from the output and paste it into `wrangler.toml`:

```toml
[[d1_databases]]
binding       = "DB"
database_name = "ois-discovery"
database_id   = "PASTE_YOUR_ID_HERE"
```

### 3. Run the schema migration

```bash
wrangler d1 execute ois-discovery --file=schema.sql
```

### 4. Set secrets

```bash
wrangler secret put WEBAUTHN_VERIFY_ORIGIN
# → enter: true

wrangler secret put ALLOWED_ORIGINS
# → enter: https://PRYSYM.github.io,http://localhost:8080

wrangler secret put CHALLENGE_TTL_SECONDS
# → enter: 300
```

### 5. Deploy

```bash
wrangler deploy
```

Note the live URL printed in the output — e.g. `https://ois-discovery.YOUR_ACCOUNT.workers.dev`.

### 6. Update the PWA default server URL

Open `pwa/app.js` and set:

```js
const DEFAULT_SERVER_URL = "https://ois-discovery.YOUR_ACCOUNT.workers.dev";
```

Or if you add a custom domain (see below): `"https://registry.prysym.app"`.

### 7. (Optional) Add a custom domain

In the Cloudflare dashboard → Workers & Pages → `ois-discovery` → Settings → Custom Domains → Add.

---

## Local development

```bash
# Start local dev server (Miniflare + local D1)
wrangler dev --local

# Apply schema to local D1
wrangler d1 execute ois-discovery --local --file=schema.sql
```

The worker is available at `http://localhost:8787`.

---

## Testing

```bash
npm test
```

Tests run with Miniflare (in-memory D1, `WEBAUTHN_VERIFY_ORIGIN=false`).
They use real P-256 key pairs and proper DER-encoded ECDSA signatures.

---

## Smoke test after deploy

1. Open the live PWA at `https://PRYSYM.github.io/open-identity-symbols/app/`
2. Click **Server Config** → enter your deployed worker URL
3. Generate an identity → click **Publish** → verify "Published to …" appears
4. Clear `localStorage` → use **Recover from discovery server** → verify same symbols appear

---

## Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WEBAUTHN_VERIFY_ORIGIN` | Verify RP origin + rpIdHash in assertions | `"true"` |
| `ALLOWED_ORIGINS` | Comma-separated CORS allowed origins | `"https://PRYSYM.github.io"` |
| `CHALLENGE_TTL_SECONDS` | Challenge token lifetime | `"300"` |

---

## Admin Setup

### 1. Generate a key

```bash
openssl rand -hex 32
```

### 2. Set the secret

```bash
cd worker
wrangler secret put ADMIN_API_KEY
# → paste the key from step 1
```

Keep this key out of version control. The dashboard reads it from your browser's `localStorage` only.

### 3. Open the dashboard

Navigate to `https://PRYSYM.github.io/open-identity-symbols/admin.html`, enter your worker URL and API key, and click **Connect**.

### Admin endpoints

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/admin/stats` | Bearer token |
| `GET` | `/admin/identities?limit=&offset=&q=` | Bearer token |
| `DELETE` | `/admin/identity/:symbol_id` | Bearer token |
| `DELETE` | `/identity` | WebAuthn assertion (user self-delete) |

---

## Relationship to `discovery/` (FastAPI)

`discovery/` is the self-hostable reference implementation (PostgreSQL, Docker).
This worker is the PRYSYM-hosted public registry. Both implement the same REST API.
The FastAPI path is unchanged — users can still self-host.
