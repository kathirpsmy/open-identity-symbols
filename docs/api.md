# API Reference

Base URL: `/api/v1`

Interactive docs available at `/docs` (Swagger UI) and `/redoc`.

---

## Auth

### POST /auth/register

Register a new account. Returns TOTP QR code for 2FA setup.

**Request**
```json
{ "email": "user@example.com", "password": "StrongPass1" }
```

**Response 201**
```json
{
  "message": "Registration successful...",
  "totp_qr": "data:image/png;base64,...",
  "totp_secret": "BASE32SECRET"
}
```

### POST /auth/confirm-totp

Confirm TOTP setup after scanning QR. Requires Bearer token (from manual token creation or via a temporary mechanism). Marks account as active.

**Request**
```json
{ "totp_code": "123456" }
```

**Response 200**
```json
{ "access_token": "...", "token_type": "bearer" }
```

### POST /auth/login

**Request**
```json
{ "email": "user@example.com", "password": "StrongPass1", "totp_code": "123456" }
```

**Response 200**
```json
{ "access_token": "...", "token_type": "bearer" }
```

---

## Identity

All identity write endpoints require `Authorization: Bearer <token>`.

### POST /identity/generate

Generate a unique 3-symbol ID for the authenticated user. Can only be called once per user.

**Response 201**
```json
{
  "symbol_id": "⚙-🌊-🔥",
  "alias": "gear-wave-fire",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### GET /identity/me

Get the authenticated user's identity.

### GET /identity/{symbol_id}

Public lookup by symbol ID.

---

## Profile

### GET /profile/me *(auth required)*

Returns full profile including private fields.

### PUT /profile/me *(auth required)*

**Request**
```json
{
  "data": { "display_name": "Alice", "bio": "Hello", "location": "Earth" },
  "visibility": { "display_name": "public", "bio": "private", "location": "public" }
}
```

### GET /profile/{symbol_id}

Returns only `public` fields.

---

## Search

### GET /search?q={query}

Case-insensitive substring search on `symbol_id` and `alias`.

| Param | Type | Default | Max |
|-------|------|---------|-----|
| `q` | string | required | 100 chars |
| `limit` | int | 20 | 100 |

**Response 200** — array of public profile objects.
