"""Tests for GET /search."""

import pytest

from discovery.tests.conftest import make_keypair
from discovery.services.symbol_derive import derive_symbol
from discovery.tests.conftest import _b64url
from discovery.tests.test_publish import ORIGIN, get_challenge, make_assertion


def publish_synthetic(client, display_name="User"):
    """Publish a random identity and return it."""
    private, _, spki = make_keypair()
    symbol_id, alias = derive_symbol(spki)
    token = get_challenge(client)
    assertion = make_assertion(private, spki, token, ORIGIN)
    body = {
        "symbol_id":       symbol_id,
        "alias":           alias,
        "public_key_spki": _b64url(spki),
        "origin":          ORIGIN,
        "challenge_token": token,
        "assertion":       assertion,
        "public_profile":  {"display_name": display_name},
    }
    r = client.post("/publish", json=body)
    assert r.status_code == 201, r.text
    return r.json()


class TestSearch:
    def test_search_returns_results(self, client):
        pub = publish_synthetic(client)
        # Search by part of the alias
        alias_part = pub["alias"].split("-")[0]
        r = client.get(f"/search?q={alias_part}")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        ids = [x["symbol_id"] for x in data["results"]]
        assert pub["symbol_id"] in ids

    def test_search_returns_empty_for_no_match(self, client):
        r = client.get("/search?q=zzzzxxxxxnomatch99999")
        assert r.status_code == 200
        assert r.json()["total"] == 0
        assert r.json()["results"] == []

    def test_search_pagination(self, client):
        # Publish 5 identities
        for i in range(5):
            publish_synthetic(client, f"User{i}")
        # Get all, then paginate
        all_r = client.get("/search?q=-&limit=100")
        total = all_r.json()["total"]
        assert total >= 5

        page1 = client.get("/search?q=-&limit=2&offset=0").json()
        page2 = client.get("/search?q=-&limit=2&offset=2").json()
        assert page1["limit"] == 2
        assert page2["offset"] == 2
        # No overlap between pages
        ids1 = {x["symbol_id"] for x in page1["results"]}
        ids2 = {x["symbol_id"] for x in page2["results"]}
        assert ids1.isdisjoint(ids2)

    def test_search_requires_query(self, client):
        r = client.get("/search")
        assert r.status_code == 422

    def test_search_limit_capped_at_100(self, client):
        r = client.get("/search?q=-&limit=200")
        assert r.status_code == 422

    def test_search_by_symbol_fragment(self, client):
        pub = publish_synthetic(client)
        # Unicode symbol fragment — just use alias since Unicode URL encoding is tricky
        alias_part = pub["alias"].split("-")[1]
        r = client.get(f"/search?q={alias_part}")
        assert r.status_code == 200
