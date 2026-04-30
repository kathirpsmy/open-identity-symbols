"""
Tests for admin API (GET /admin/stats, GET /admin/identities,
DELETE /admin/identity/{symbol_id}) and user self-delete (DELETE /identity).
"""

import os
import pytest

from discovery.tests.conftest import _b64url, make_assertion, make_keypair
from discovery.services.symbol_derive import derive_symbol

ORIGIN    = "http://localhost:8001"
ADMIN_KEY = "test-admin-key-abc123"
ADMIN_HDR = {"Authorization": f"Bearer {ADMIN_KEY}"}


def get_challenge(client) -> str:
    return client.get("/challenge").json()["token"]


def publish_identity(client, identity_key, origin=ORIGIN):
    token     = get_challenge(client)
    assertion = make_assertion(identity_key["private_key"], identity_key["spki_bytes"], token, origin)
    r = client.post("/publish", json={
        "symbol_id":       identity_key["symbol_id"],
        "alias":           identity_key["alias"],
        "public_key_spki": identity_key["spki_b64url"],
        "origin":          origin,
        "challenge_token": token,
        "assertion":       assertion,
    })
    assert r.status_code == 201, r.text
    return r.json()


def make_identity_key():
    priv, _, spki = make_keypair()
    sym, alias    = derive_symbol(spki)
    return {
        "private_key": priv, "spki_bytes": spki,
        "spki_b64url": _b64url(spki), "symbol_id": sym, "alias": alias,
    }


@pytest.fixture(autouse=True)
def set_admin_key():
    from discovery.config import settings
    original = settings.ADMIN_API_KEY
    settings.ADMIN_API_KEY = ADMIN_KEY
    yield
    settings.ADMIN_API_KEY = original


# ─── /admin/stats ─────────────────────────────────────────────────────────────

class TestAdminStats:
    def test_stats_returns_expected_shape(self, client, identity_key):
        publish_identity(client, identity_key)
        r = client.get("/admin/stats", headers=ADMIN_HDR)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["total_identities"] == 1
        assert "registrations_today"    in data
        assert "registrations_last_7d"  in data
        assert "registrations_last_30d" in data

    def test_stats_empty_registry(self, client):
        r = client.get("/admin/stats", headers=ADMIN_HDR)
        assert r.status_code == 200
        assert r.json()["total_identities"] == 0

    def test_stats_no_auth_rejected(self, client):
        r = client.get("/admin/stats")
        assert r.status_code == 401

    def test_stats_wrong_key_rejected(self, client):
        r = client.get("/admin/stats", headers={"Authorization": "Bearer wrong-key"})
        assert r.status_code == 401


# ─── /admin/identities ────────────────────────────────────────────────────────

class TestAdminIdentities:
    def test_list_returns_all(self, client, identity_key):
        publish_identity(client, identity_key)
        r = client.get("/admin/identities", headers=ADMIN_HDR)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["symbol_id"] == identity_key["symbol_id"]

    def test_pagination_limit(self, client):
        for _ in range(3):
            publish_identity(client, make_identity_key())
        r = client.get("/admin/identities?limit=2&offset=0", headers=ADMIN_HDR)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 3
        assert len(data["results"]) == 2

    def test_pagination_offset(self, client):
        for _ in range(3):
            publish_identity(client, make_identity_key())
        r = client.get("/admin/identities?limit=2&offset=2", headers=ADMIN_HDR)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 3
        assert len(data["results"]) == 1

    def test_search_filter_matches(self, client, identity_key):
        publish_identity(client, identity_key)
        q = identity_key["alias"].split("-")[0]
        r = client.get(f"/admin/identities?q={q}", headers=ADMIN_HDR)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_search_no_match_returns_empty(self, client, identity_key):
        publish_identity(client, identity_key)
        r = client.get("/admin/identities?q=zzznomatch999", headers=ADMIN_HDR)
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_list_no_auth_rejected(self, client):
        r = client.get("/admin/identities")
        assert r.status_code == 401


# ─── DELETE /admin/identity/{symbol_id} ───────────────────────────────────────

class TestAdminDelete:
    def test_delete_removes_row(self, client, identity_key):
        publish_identity(client, identity_key)
        r = client.delete(
            f"/admin/identity/{identity_key['symbol_id']}", headers=ADMIN_HDR
        )
        assert r.status_code == 204
        r2 = client.get(f"/lookup/{identity_key['symbol_id']}")
        assert r2.status_code == 404

    def test_delete_unknown_symbol_404(self, client):
        r = client.delete("/admin/identity/nonexistent-symbol", headers=ADMIN_HDR)
        assert r.status_code == 404

    def test_delete_no_auth_rejected(self, client, identity_key):
        publish_identity(client, identity_key)
        r = client.delete(f"/admin/identity/{identity_key['symbol_id']}")
        assert r.status_code == 401

    def test_stats_decrement_after_delete(self, client, identity_key):
        publish_identity(client, identity_key)
        client.delete(f"/admin/identity/{identity_key['symbol_id']}", headers=ADMIN_HDR)
        r = client.get("/admin/stats", headers=ADMIN_HDR)
        assert r.json()["total_identities"] == 0


# ─── DELETE /identity (self-delete) ───────────────────────────────────────────

class TestSelfDelete:
    def test_self_delete_removes_row(self, client, identity_key):
        publish_identity(client, identity_key)
        token     = get_challenge(client)
        assertion = make_assertion(identity_key["private_key"], identity_key["spki_bytes"], token, ORIGIN)
        r = client.request("DELETE", "/identity", json={
            "symbol_id":       identity_key["symbol_id"],
            "challenge_token": token,
            "assertion":       assertion,
        })
        assert r.status_code == 204, r.text
        r2 = client.get(f"/lookup/{identity_key['symbol_id']}")
        assert r2.status_code == 404

    def test_self_delete_unknown_symbol_404(self, client, identity_key):
        token     = get_challenge(client)
        assertion = make_assertion(identity_key["private_key"], identity_key["spki_bytes"], token, ORIGIN)
        r = client.request("DELETE", "/identity", json={
            "symbol_id":       "nonexistent-symbol",
            "challenge_token": token,
            "assertion":       assertion,
        })
        assert r.status_code == 404

    def test_self_delete_wrong_challenge_422(self, client, identity_key):
        publish_identity(client, identity_key)
        fake_token = os.urandom(32).hex()
        assertion  = make_assertion(identity_key["private_key"], identity_key["spki_bytes"], fake_token, ORIGIN)
        r = client.request("DELETE", "/identity", json={
            "symbol_id":       identity_key["symbol_id"],
            "challenge_token": fake_token,
            "assertion":       assertion,
        })
        assert r.status_code == 422
        assert "Invalid or unknown challenge" in r.json()["detail"]

    def test_self_delete_bad_signature_401(self, client, identity_key):
        publish_identity(client, identity_key)
        other_priv, _, other_spki = make_keypair()
        token     = get_challenge(client)
        assertion = make_assertion(other_priv, other_spki, token, ORIGIN)
        r = client.request("DELETE", "/identity", json={
            "symbol_id":       identity_key["symbol_id"],
            "challenge_token": token,
            "assertion":       assertion,
        })
        assert r.status_code == 401
        assert "Assertion verification failed" in r.json()["detail"]

    def test_challenge_single_use_on_self_delete(self, client, identity_key):
        publish_identity(client, identity_key)
        token     = get_challenge(client)
        assertion = make_assertion(identity_key["private_key"], identity_key["spki_bytes"], token, ORIGIN)
        body = {
            "symbol_id":       identity_key["symbol_id"],
            "challenge_token": token,
            "assertion":       assertion,
        }
        r1 = client.request("DELETE", "/identity", json=body)
        assert r1.status_code == 204
        # Re-register same identity so we can try to reuse the token
        publish_identity(client, identity_key)
        r2 = client.request("DELETE", "/identity", json=body)
        assert r2.status_code == 422
