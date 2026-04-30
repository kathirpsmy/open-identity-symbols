# Discovery Server API

| Instance | Base URL |
|----------|----------|
| PRYSYM hosted (Cloudflare Worker) | `https://ois-discovery.kathirpsmy.workers.dev`|
| Self-hosted default (Docker) | `http://localhost:8001` |

The Cloudflare Worker and the FastAPI self-host implement the same REST API contract.
FastAPI also exposes interactive docs at `/docs` (Swagger UI) when running.

---

## Endpoints

### `GET /challenge`

Request a one-time WebAuthn challenge before publishing.

**Response `200`**
```json
{
  "challenge": "a3f9e2b1c4d5..."
}
```

The challenge is a random 32-byte hex string. It is consumed on first use.

---

### `POST /publish`

Publish a symbol identity with a WebAuthn proof of ownership.

**Request body**
```json
{
  "symbol_id":       "⚙-🌊-🔥",
  "alias":           "gear-wave-fire",
  "public_key":      "<base64url SPKI DER>",
  "credential_id":   "<base64url>",
  "client_data_json": "<base64url>",
  "authenticator_data": "<base64url>",
  "signature":       "<base64url>"
}
```

**Validation**
1. The WebAuthn assertion is verified against the submitted `public_key`
2. The server re-derives the symbol ID from `public_key` and confirms it matches `symbol_id`
3. Duplicate `symbol_id` returns `409 Conflict`

**Response `201`**
```json
{
  "symbol_id": "⚙-🌊-🔥",
  "alias":     "gear-wave-fire"
}
```

---

### `GET /lookup/{symbol_id}`

Look up a published identity by its symbol ID.

**Example:** `GET /lookup/⚙-🌊-🔥`

**Response `200`**
```json
{
  "symbol_id":  "⚙-🌊-🔥",
  "alias":      "gear-wave-fire",
  "public_key": "<base64url SPKI DER>",
  "created_at": "2025-01-15T10:23:00Z"
}
```

**Response `404`** if not found.

---

### `GET /search?q=`

Full-text search across symbol IDs and aliases.

**Example:** `GET /search?q=gear`

**Response `200`**
```json
[
  {
    "symbol_id": "⚙-🌊-🔥",
    "alias":     "gear-wave-fire"
  }
]
```

Returns up to 20 results ordered by relevance.

---

---

### `GET /admin/stats`

Returns registry analytics. Requires `Authorization: Bearer <ADMIN_API_KEY>` header.

**Response `200`**
```json
{
  "total_identities":       312,
  "registrations_today":    4,
  "registrations_last_7d":  18,
  "registrations_last_30d": 67,
  "most_recent":            "2026-04-29T10:22:00"
}
```

**Response `401`** if key is missing or wrong.

---

### `GET /admin/identities`

Paginated list of all registered identities. Requires admin auth.

**Query params:** `limit` (1–100, default 20), `offset` (default 0), `q` (optional filter on symbol or alias)

**Response `200`**
```json
{
  "results": [ ...identity objects... ],
  "total":   312,
  "limit":   20,
  "offset":  0
}
```

---

### `DELETE /admin/identity/:symbol_id`

Hard-delete an identity by symbol ID. Requires admin auth.

**Response `204`** on success. **Response `404`** if not found.

---

### `DELETE /identity`

User self-delete — no admin key required. Caller must prove ownership via a WebAuthn assertion.

**Request body**
```json
{
  "symbol_id": "⚡-🌊-🔥",
  "challenge_token": "<hex token from GET /challenge>",
  "assertion": {
    "client_data_json":   "<base64url>",
    "authenticator_data": "<base64url>",
    "signature":          "<base64url>"
  }
}
```

**Response `204`** on success. **Response `401`** if assertion fails. **Response `422`** if challenge is invalid or expired.

---

## Error Responses

| Status | Meaning |
|--------|---------|
| `400`  | Invalid request body or WebAuthn verification failed |
| `404`  | Symbol ID not found |
| `409`  | Symbol ID already published |
| `422`  | Validation error (Pydantic) |

---

## Running Locally

**Cloudflare Worker:**
```bash
cd worker && wrangler dev --local
# → http://localhost:8787
```

**Docker Compose (FastAPI):**
```bash
docker compose up
# → http://localhost:8001  (Swagger UI: /docs)
```

See [discovery-server.md](./discovery-server.md) for full setup guide.
