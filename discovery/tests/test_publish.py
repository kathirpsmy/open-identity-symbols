"""
Tests for POST /publish and PUT /profile.
Uses synthetic P-256 assertions (no browser required).
"""

import os
import pytest

from discovery.tests.conftest import _b64url, make_assertion


ORIGIN = "http://localhost:8001"


def get_challenge(client) -> str:
    return client.get("/challenge").json()["token"]


def publish_body(client, identity_key, origin=ORIGIN, profile=None) -> dict:
    token = get_challenge(client)
    assertion = make_assertion(identity_key["private_key"], identity_key["spki_bytes"], token, origin)
    return {
        "symbol_id":       identity_key["symbol_id"],
        "alias":           identity_key["alias"],
        "public_key_spki": identity_key["spki_b64url"],
        "origin":          origin,
        "challenge_token": token,
        "assertion":       assertion,
        "public_profile":  profile or {"display_name": "Test User"},
    }


class TestPublish:
    def test_publish_creates_identity(self, client, identity_key):
        body = publish_body(client, identity_key)
        r = client.post("/publish", json=body)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["symbol_id"]     == identity_key["symbol_id"]
        assert data["alias"]         == identity_key["alias"]
        assert data["public_key_id"] == identity_key["public_key_id"]

    def test_publish_is_idempotent_for_same_key(self, client, identity_key):
        client.post("/publish", json=publish_body(client, identity_key))
        r2 = client.post("/publish", json=publish_body(client, identity_key, profile={"display_name": "Updated"}))
        assert r2.status_code == 201
        # Lookup should show updated profile
        r3 = client.get(f"/lookup/{identity_key['symbol_id']}")
        assert r3.json()["public_profile"]["display_name"] == "Updated"

    def test_challenge_is_single_use(self, client, identity_key):
        token = get_challenge(client)
        assertion = make_assertion(identity_key["private_key"], identity_key["spki_bytes"], token, ORIGIN)
        body = {
            "symbol_id":       identity_key["symbol_id"],
            "alias":           identity_key["alias"],
            "public_key_spki": identity_key["spki_b64url"],
            "origin":          ORIGIN,
            "challenge_token": token,
            "assertion":       assertion,
        }
        r1 = client.post("/publish", json=body)
        assert r1.status_code == 201
        # Reuse the same token
        r2 = client.post("/publish", json=body)
        assert r2.status_code == 422
        assert "Invalid or unknown challenge" in r2.json()["detail"]

    def test_mismatched_symbol_id_rejected(self, client, identity_key):
        from discovery.tests.conftest import make_keypair
        from discovery.services.symbol_derive import derive_symbol
        _, _, other_spki = make_keypair()
        other_symbol, other_alias = derive_symbol(other_spki)

        token = get_challenge(client)
        assertion = make_assertion(identity_key["private_key"], identity_key["spki_bytes"], token, ORIGIN)
        body = {
            "symbol_id":       other_symbol,   # doesn't match identity_key's public key
            "alias":           other_alias,
            "public_key_spki": identity_key["spki_b64url"],
            "origin":          ORIGIN,
            "challenge_token": token,
            "assertion":       assertion,
        }
        r = client.post("/publish", json=body)
        assert r.status_code == 422
        assert "symbol_id mismatch" in r.json()["detail"]

    def test_invalid_assertion_signature_rejected(self, client, identity_key):
        from discovery.tests.conftest import make_keypair
        other_private, _, other_spki = make_keypair()

        token = get_challenge(client)
        # Sign with a different key
        assertion = make_assertion(other_private, other_spki, token, ORIGIN)
        body = {
            "symbol_id":       identity_key["symbol_id"],
            "alias":           identity_key["alias"],
            "public_key_spki": identity_key["spki_b64url"],
            "origin":          ORIGIN,
            "challenge_token": token,
            "assertion":       assertion,
        }
        r = client.post("/publish", json=body)
        assert r.status_code == 401
        assert "Assertion verification failed" in r.json()["detail"]

    def test_unknown_challenge_rejected(self, client, identity_key):
        fake_token = os.urandom(32).hex()
        assertion = make_assertion(identity_key["private_key"], identity_key["spki_bytes"], fake_token, ORIGIN)
        body = {
            "symbol_id":       identity_key["symbol_id"],
            "alias":           identity_key["alias"],
            "public_key_spki": identity_key["spki_b64url"],
            "origin":          ORIGIN,
            "challenge_token": fake_token,
            "assertion":       assertion,
        }
        r = client.post("/publish", json=body)
        assert r.status_code == 422
        assert "Invalid or unknown challenge" in r.json()["detail"]

    def test_invalid_origin_in_body_rejected(self, client, identity_key):
        token = get_challenge(client)
        assertion = make_assertion(identity_key["private_key"], identity_key["spki_bytes"], token, ORIGIN)
        body = {
            "symbol_id":       identity_key["symbol_id"],
            "alias":           identity_key["alias"],
            "public_key_spki": identity_key["spki_b64url"],
            "origin":          "ftp://evil.com",   # not https or localhost
            "challenge_token": token,
            "assertion":       assertion,
        }
        r = client.post("/publish", json=body)
        assert r.status_code == 422


class TestProfileUpdate:
    def _publish(self, client, identity_key):
        body = publish_body(client, identity_key)
        r = client.post("/publish", json=body)
        assert r.status_code == 201

    def test_update_profile_succeeds(self, client, identity_key):
        self._publish(client, identity_key)
        token = get_challenge(client)
        assertion = make_assertion(identity_key["private_key"], identity_key["spki_bytes"], token, ORIGIN)
        r = client.put("/profile", json={
            "symbol_id":       identity_key["symbol_id"],
            "origin":          ORIGIN,
            "challenge_token": token,
            "assertion":       assertion,
            "public_profile":  {"display_name": "New Name", "bio": "Hello world"},
        })
        assert r.status_code == 200
        assert r.json()["public_profile"]["display_name"] == "New Name"

    def test_update_nonexistent_symbol_returns_404(self, client, identity_key):
        token = get_challenge(client)
        assertion = make_assertion(identity_key["private_key"], identity_key["spki_bytes"], token, ORIGIN)
        r = client.put("/profile", json={
            "symbol_id":       "⚙-🌊-🔥",
            "origin":          ORIGIN,
            "challenge_token": token,
            "assertion":       assertion,
            "public_profile":  {},
        })
        assert r.status_code == 404

    def test_wrong_key_cannot_update_profile(self, client, identity_key):
        self._publish(client, identity_key)
        from discovery.tests.conftest import make_keypair
        other_private, _, other_spki = make_keypair()
        token = get_challenge(client)
        # Sign with attacker's key
        assertion = make_assertion(other_private, other_spki, token, ORIGIN)
        r = client.put("/profile", json={
            "symbol_id":       identity_key["symbol_id"],
            "origin":          ORIGIN,
            "challenge_token": token,
            "assertion":       assertion,
            "public_profile":  {"display_name": "Hacked"},
        })
        assert r.status_code == 401
