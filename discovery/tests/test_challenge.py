"""Tests for GET /challenge."""

import time
from datetime import datetime, timezone

import pytest


class TestGetChallenge:
    def test_returns_token_and_expiry(self, client):
        r = client.get("/challenge")
        assert r.status_code == 200
        body = r.json()
        assert "token" in body
        assert "expires_at" in body
        # Token must be 64 hex chars (32 bytes)
        assert len(body["token"]) == 64
        assert all(c in "0123456789abcdef" for c in body["token"])

    def test_each_call_returns_unique_token(self, client):
        tokens = {client.get("/challenge").json()["token"] for _ in range(5)}
        assert len(tokens) == 5

    def test_expiry_is_in_the_future(self, client):
        r = client.get("/challenge")
        expires_at = datetime.fromisoformat(r.json()["expires_at"].replace("Z", "+00:00"))
        assert expires_at > datetime.now(timezone.utc)
