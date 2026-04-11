"""Tests for admin API routes."""

import pytest
from backend.core.security import create_access_token, hash_password, generate_totp_secret
from backend.tests.conftest import TestingSessionLocal


def _make_user(email: str, is_admin: bool = False, is_active: bool = True) -> str:
    """Insert a user and return a valid Bearer token for them."""
    from backend.models.user import User

    db = TestingSessionLocal()
    user = User(
        email=email,
        password_hash=hash_password("Test1234"),
        totp_secret=generate_totp_secret(),
        totp_confirmed=True,
        is_admin=is_admin,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.close()
    return create_access_token(subject=email)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestAdminAccess:
    def test_non_admin_cannot_list_users(self, client):
        token = _make_user("nonadmin_list@example.com")
        res = client.get("/api/v1/admin/users", headers=_auth(token))
        assert res.status_code == 403

    def test_unauthenticated_request_blocked(self, client):
        res = client.get("/api/v1/admin/users")
        assert res.status_code == 403

    def test_admin_can_list_users(self, client):
        token = _make_user("admin_list@example.com", is_admin=True)
        res = client.get("/api/v1/admin/users", headers=_auth(token))
        assert res.status_code == 200
        assert isinstance(res.json(), list)


class TestUserManagement:
    def test_admin_deactivates_user(self, client):
        admin_token = _make_user("admin_deact@example.com", is_admin=True)
        _make_user("target_deact@example.com")

        # Fetch user id
        users = client.get("/api/v1/admin/users", headers=_auth(admin_token)).json()
        target = next(u for u in users if u["email"] == "target_deact@example.com")

        res = client.patch(
            f"/api/v1/admin/users/{target['id']}/deactivate",
            headers=_auth(admin_token),
        )
        assert res.status_code == 200
        assert res.json()["is_active"] is False

    def test_admin_activates_user(self, client):
        admin_token = _make_user("admin_act@example.com", is_admin=True)
        _make_user("target_act@example.com", is_active=False)

        users = client.get("/api/v1/admin/users", headers=_auth(admin_token)).json()
        target = next(u for u in users if u["email"] == "target_act@example.com")

        res = client.patch(
            f"/api/v1/admin/users/{target['id']}/activate",
            headers=_auth(admin_token),
        )
        assert res.status_code == 200
        assert res.json()["is_active"] is True

    def test_admin_cannot_deactivate_self(self, client):
        admin_token = _make_user("admin_selfdeact@example.com", is_admin=True)

        users = client.get("/api/v1/admin/users", headers=_auth(admin_token)).json()
        self_user = next(u for u in users if u["email"] == "admin_selfdeact@example.com")

        res = client.patch(
            f"/api/v1/admin/users/{self_user['id']}/deactivate",
            headers=_auth(admin_token),
        )
        assert res.status_code == 400

    def test_deactivate_nonexistent_user_returns_404(self, client):
        admin_token = _make_user("admin_404@example.com", is_admin=True)
        res = client.patch("/api/v1/admin/users/999999/deactivate", headers=_auth(admin_token))
        assert res.status_code == 404

    def test_deactivated_user_blocked_on_protected_routes(self, client):
        admin_token = _make_user("admin_block@example.com", is_admin=True)
        target_token = _make_user("blocked_user@example.com")

        # Verify works before deactivation
        assert client.get("/api/v1/identity/me", headers=_auth(target_token)).status_code == 404

        users = client.get("/api/v1/admin/users", headers=_auth(admin_token)).json()
        target = next(u for u in users if u["email"] == "blocked_user@example.com")
        client.patch(f"/api/v1/admin/users/{target['id']}/deactivate", headers=_auth(admin_token))

        # Token still valid but user is_active=False
        res = client.get("/api/v1/identity/me", headers=_auth(target_token))
        assert res.status_code == 401


class TestAnalytics:
    def test_admin_gets_analytics(self, client):
        token = _make_user("admin_analytics@example.com", is_admin=True)
        res = client.get("/api/v1/admin/analytics", headers=_auth(token))
        assert res.status_code == 200
        body = res.json()
        assert "total_users" in body
        assert "active_users" in body
        assert "inactive_users" in body
        assert "admin_users" in body
        assert "total_identities" in body
        assert "new_users_last_7_days" in body
        assert body["total_users"] >= 1  # at least our admin user
        assert body["admin_users"] >= 1

    def test_non_admin_blocked_from_analytics(self, client):
        token = _make_user("nonadmin_analytics@example.com")
        res = client.get("/api/v1/admin/analytics", headers=_auth(token))
        assert res.status_code == 403
