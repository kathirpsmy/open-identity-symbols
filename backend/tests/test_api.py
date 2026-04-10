"""Tests for identity, profile, and search API routes."""

import pytest
from backend.core.security import create_access_token
from backend.tests.conftest import TestingSessionLocal


def _auth_header(email: str) -> dict:
    token = create_access_token(subject=email)
    return {"Authorization": f"Bearer {token}"}


def _setup_confirmed_user(client, email: str):
    """Insert a TOTP-confirmed user directly into the test DB."""
    from backend.models.user import User
    from backend.core.security import hash_password, generate_totp_secret

    db = TestingSessionLocal()
    user = User(
        email=email,
        password_hash=hash_password("Test1234"),
        totp_secret=generate_totp_secret(),
        totp_confirmed=True,
    )
    db.add(user)
    db.commit()
    db.close()


class TestIdentity:
    def test_generate_identity(self, client):
        email = "id_gen@example.com"
        _setup_confirmed_user(client, email)

        res = client.post("/api/v1/identity/generate", headers=_auth_header(email))
        assert res.status_code == 201
        body = res.json()
        assert "symbol_id" in body
        assert "alias" in body
        assert body["symbol_id"].count("-") == 2
        assert body["alias"].count("-") == 2

    def test_generate_identity_twice_returns_conflict(self, client):
        email = "id_twice@example.com"
        _setup_confirmed_user(client, email)

        client.post("/api/v1/identity/generate", headers=_auth_header(email))
        res = client.post("/api/v1/identity/generate", headers=_auth_header(email))
        assert res.status_code == 409

    def test_get_my_identity(self, client):
        email = "id_me@example.com"
        _setup_confirmed_user(client, email)

        client.post("/api/v1/identity/generate", headers=_auth_header(email))
        res = client.get("/api/v1/identity/me", headers=_auth_header(email))
        assert res.status_code == 200
        assert "symbol_id" in res.json()

    def test_get_identity_no_auth_returns_401(self, client):
        res = client.post("/api/v1/identity/generate")
        assert res.status_code == 403  # HTTPBearer returns 403 when no token provided

    def test_get_identity_by_symbol_id(self, client):
        email = "id_lookup@example.com"
        _setup_confirmed_user(client, email)

        gen_res = client.post("/api/v1/identity/generate", headers=_auth_header(email))
        symbol_id = gen_res.json()["symbol_id"]

        res = client.get(f"/api/v1/identity/{symbol_id}")
        assert res.status_code == 200
        assert res.json()["symbol_id"] == symbol_id

    def test_get_nonexistent_identity_returns_404(self, client):
        res = client.get("/api/v1/identity/X-Y-Z")
        assert res.status_code == 404


class TestProfile:
    def test_get_empty_profile(self, client):
        email = "profile_empty@example.com"
        _setup_confirmed_user(client, email)

        res = client.get("/api/v1/profile/me", headers=_auth_header(email))
        assert res.status_code == 200
        body = res.json()
        assert "data" in body
        assert "visibility" in body

    def test_update_profile(self, client):
        email = "profile_update@example.com"
        _setup_confirmed_user(client, email)

        res = client.put(
            "/api/v1/profile/me",
            json={
                "data": {"display_name": "Alice", "bio": "Hello world"},
                "visibility": {"display_name": "public", "bio": "private"},
            },
            headers=_auth_header(email),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["data"]["display_name"] == "Alice"
        assert body["visibility"]["display_name"] == "public"
        assert body["visibility"]["bio"] == "private"

    def test_public_profile_shows_only_public_fields(self, client):
        email = "profile_public@example.com"
        _setup_confirmed_user(client, email)

        gen_res = client.post("/api/v1/identity/generate", headers=_auth_header(email))
        symbol_id = gen_res.json()["symbol_id"]

        client.put(
            "/api/v1/profile/me",
            json={
                "data": {"display_name": "Bob", "bio": "Secret bio"},
                "visibility": {"display_name": "public", "bio": "private"},
            },
            headers=_auth_header(email),
        )

        pub_res = client.get(f"/api/v1/profile/{symbol_id}")
        assert pub_res.status_code == 200
        pub_data = pub_res.json()["data"]
        assert pub_data.get("display_name") == "Bob"
        assert "bio" not in pub_data  # private field hidden


class TestSearch:
    def test_search_returns_results(self, client):
        email = "search_user@example.com"
        _setup_confirmed_user(client, email)

        gen_res = client.post("/api/v1/identity/generate", headers=_auth_header(email))
        alias = gen_res.json()["alias"]
        first_word = alias.split("-")[0]

        res = client.get(f"/api/v1/search?q={first_word}")
        assert res.status_code == 200
        assert isinstance(res.json(), list)
        assert any(r["alias"].startswith(first_word) for r in res.json())

    def test_search_empty_query_rejected(self, client):
        res = client.get("/api/v1/search?q=")
        assert res.status_code == 422

    def test_search_no_results(self, client):
        res = client.get("/api/v1/search?q=zzznomatchxxx")
        assert res.status_code == 200
        assert res.json() == []


class TestHealth:
    def test_health_endpoint(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
