"""Tests for GET /lookup/{symbol_id}, /lookup/alias/{alias}, /lookup/key/{id}."""

import pytest

from discovery.tests.test_publish import publish_body


class TestLookup:
    def _publish(self, client, identity_key):
        r = client.post("/publish", json=publish_body(client, identity_key, profile={"display_name": "Alice"}))
        assert r.status_code == 201
        return r.json()

    def test_lookup_by_symbol_id(self, client, identity_key):
        self._publish(client, identity_key)
        r = client.get(f"/lookup/{identity_key['symbol_id']}")
        assert r.status_code == 200
        data = r.json()
        assert data["symbol_id"]    == identity_key["symbol_id"]
        assert data["alias"]        == identity_key["alias"]
        assert data["public_key_id"] == identity_key["public_key_id"]
        assert data["public_key_spki"] == identity_key["spki_b64url"]
        assert data["public_profile"]["display_name"] == "Alice"

    def test_lookup_by_alias(self, client, identity_key):
        self._publish(client, identity_key)
        r = client.get(f"/lookup/alias/{identity_key['alias']}")
        assert r.status_code == 200
        assert r.json()["symbol_id"] == identity_key["symbol_id"]

    def test_lookup_by_key_id(self, client, identity_key):
        self._publish(client, identity_key)
        r = client.get(f"/lookup/key/{identity_key['public_key_id']}")
        assert r.status_code == 200
        assert r.json()["symbol_id"] == identity_key["symbol_id"]

    def test_lookup_unknown_symbol_returns_404(self, client, identity_key):
        r = client.get("/lookup/⚙-🌊-🔥")
        assert r.status_code == 404

    def test_lookup_unknown_alias_returns_404(self, client, identity_key):
        r = client.get("/lookup/alias/gear-wave-fire")
        assert r.status_code == 404

    def test_lookup_unknown_key_id_returns_404(self, client):
        r = client.get("/lookup/key/" + "aa" * 32)
        assert r.status_code == 404
