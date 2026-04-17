"""
Shared pytest fixtures for the discovery server test suite.

IMPORTANT: DATABASE_URL is overridden to SQLite (in-memory) *before* any
discovery module is imported.  This must stay at the top of this file so that
pydantic-settings reads the override when `Settings()` is first constructed,
and so that SQLAlchemy creates the engine against SQLite, not PostgreSQL.
"""

import base64
import hashlib
import json
import os
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Override DB URL to in-memory SQLite for all tests (must happen before any
# discovery import so discovery/config.py picks it up via pydantic-settings)
# ─────────────────────────────────────────────────────────────────────────────
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["WEBAUTHN_VERIFY_ORIGIN"] = "false"  # skip origin/rp_id check in tests

# Make sure repo root is on path so discovery/* can import data/*
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cryptography.hazmat.primitives.asymmetric.ec import (
    ECDSA, SECP256R1, generate_private_key,
)
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

# Import discovery modules AFTER env vars are set
from discovery.database import Base, get_db
from discovery.main import app
from discovery.services.symbol_derive import derive_symbol, public_key_id


# ─────────────────────────────────────────────────────────────────────────────
# SQLite in-memory engine (shared across test session for speed, reset per test)
# ─────────────────────────────────────────────────────────────────────────────

SQLITE_URL = "sqlite://"
# StaticPool: all threads share one in-memory connection.
# Required because Starlette's test client dispatches requests on worker threads
# that would otherwise each get their own empty SQLite connection.
_engine   = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_Session  = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _override_get_db():
    db = _Session()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True, scope="function")
def reset_db():
    """Drop and recreate all tables before each test for full isolation."""
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def client(reset_db) -> TestClient:
    """FastAPI test client wired to the in-memory SQLite DB."""
    app.dependency_overrides[get_db] = _override_get_db
    # Patch the module-level engine used in the lifespan create_all
    import discovery.database as _db
    _orig_engine = _db.engine
    _db.engine = _engine
    with TestClient(app) as c:
        yield c
    _db.engine = _orig_engine
    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Cryptographic helpers
# ─────────────────────────────────────────────────────────────────────────────

def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def make_keypair():
    """Generate a P-256 key pair and return (private_key, public_key, spki_bytes)."""
    private = generate_private_key(SECP256R1())
    public  = private.public_key()
    spki    = public.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    return private, public, spki


def make_assertion(
    private_key,
    spki_bytes: bytes,
    challenge_hex: str,
    origin: str = "http://localhost:8001",
) -> dict:
    """
    Build a synthetic but cryptographically valid WebAuthn assertion.

    clientDataJSON.type   = "webauthn.get"
    clientDataJSON.challenge = base64url(bytes.fromhex(challenge_hex))
    authenticatorData       = rpIdHash || flags(UP+UV) || signCount(0)
    signature               = ECDSA-P256(authenticatorData || SHA-256(clientDataJSON))
    """
    from urllib.parse import urlparse

    rp_id = urlparse(origin).hostname or "localhost"
    challenge_bytes = bytes.fromhex(challenge_hex)

    client_data = {
        "type":      "webauthn.get",
        "challenge": _b64url(challenge_bytes),
        "origin":    origin,
    }
    client_data_json = json.dumps(client_data, separators=(",", ":")).encode()

    rp_id_hash = hashlib.sha256(rp_id.encode()).digest()
    flags      = bytes([0x05])             # UP=1, UV=1
    sign_count = (0).to_bytes(4, "big")
    auth_data  = rp_id_hash + flags + sign_count

    verification_data = auth_data + hashlib.sha256(client_data_json).digest()
    signature = private_key.sign(verification_data, ECDSA(SHA256()))

    return {
        "credential_id":      _b64url(os.urandom(16)),
        "client_data_json":   _b64url(client_data_json),
        "authenticator_data": _b64url(auth_data),
        "signature":          _b64url(signature),
    }


# ─────────────────────────────────────────────────────────────────────────────
# identity_key fixture — a ready-to-use synthetic identity
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def identity_key():
    """A fresh P-256 key pair + derived symbol info for use in tests."""
    private, _, spki = make_keypair()
    symbol_id, alias = derive_symbol(spki)
    return {
        "private_key":   private,
        "spki_bytes":    spki,
        "spki_b64url":   _b64url(spki),
        "symbol_id":     symbol_id,
        "alias":         alias,
        "public_key_id": public_key_id(spki),
    }
