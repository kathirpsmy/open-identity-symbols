# Discovery Server API

Base URL: `http://localhost:8001` (self-hosted default)

Interactive docs available at `/docs` (Swagger UI) and `/redoc` when the server is running.

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

## Error Responses

| Status | Meaning |
|--------|---------|
| `400`  | Invalid request body or WebAuthn verification failed |
| `404`  | Symbol ID not found |
| `409`  | Symbol ID already published |
| `422`  | Validation error (Pydantic) |

---

## Running Locally

```bash
docker compose up
# Discovery API: http://localhost:8001
# Swagger UI:    http://localhost:8001/docs
```

See [discovery-server.md](./discovery-server.md) for full setup guide.
