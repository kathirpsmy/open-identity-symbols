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

### POST /auth/totp/reset *(auth required)*

Reset the authenticated user's TOTP secret. Generates a new secret, invalidates the old authenticator entry, and sets `totp_confirmed=False`. The client must call `POST /auth/confirm-totp` with the new code to re-confirm before the next login.

**Response 200**
```json
{
  "message": "TOTP has been reset...",
  "totp_qr": "data:image/png;base64,...",
  "totp_secret": "NEWBASE32SECRET"
}
```

**Errors**
- `401` — invalid or expired token

### GET /auth/me *(auth required)*

Return basic info about the currently authenticated user.

**Response 200**
```json
{ "email": "user@example.com", "is_admin": false, "is_active": true }
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

## Admin

All admin endpoints require an authenticated user with `is_admin=true`. Non-admin requests receive `403 Forbidden`.

### GET /admin/users

Return a paginated list of all users.

| Param | Type | Default |
|-------|------|---------|
| `skip` | int | 0 |
| `limit` | int | 100 |

**Response 200** — array of user objects:
```json
[
  {
    "id": 1,
    "email": "user@example.com",
    "is_active": true,
    "is_admin": false,
    "totp_confirmed": true,
    "has_identity": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### PATCH /admin/users/{user_id}/deactivate

Deactivate a user account. Blocked users receive `401` on all authenticated requests. Admins cannot deactivate their own account.

**Response 200** — updated user object.

**Errors**
- `400` — cannot deactivate own account
- `404` — user not found

### PATCH /admin/users/{user_id}/activate

Re-activate a previously deactivated user account.

**Response 200** — updated user object.

### GET /admin/analytics

Return aggregate platform statistics.

**Response 200**
```json
{
  "total_users": 120,
  "active_users": 115,
  "inactive_users": 5,
  "admin_users": 2,
  "total_identities": 98,
  "new_users_last_7_days": 14
}
```

---

## Search

### GET /search?q={query}

Case-insensitive substring search on `symbol_id` and `alias`.

| Param | Type | Default | Max |
|-------|------|---------|-----|
| `q` | string | required | 100 chars |
| `limit` | int | 20 | 100 |

**Response 200** — array of public profile objects.
