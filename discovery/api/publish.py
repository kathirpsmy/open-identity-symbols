"""
POST /publish  — register or update an identity on this discovery server.
PUT  /profile  — update the public profile of an existing identity.

Both endpoints require a valid WebAuthn assertion against a challenge token
issued by GET /challenge.  The assertion proves the caller controls the
private key corresponding to the submitted public key.

Security properties
───────────────────
1. Symbol derivation check: re-derive symbol_id from the submitted public key;
   must match the submitted symbol_id.  Prevents claiming arbitrary symbols.
2. Assertion verification: signature over (authenticatorData || SHA-256(clientDataJSON))
   must verify against the submitted public key.  Proves key ownership.
3. Challenge freshness: token must exist in the DB, not be expired, and is
   deleted after a single use (replay prevention).
"""

import base64
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from discovery.config import settings
from discovery.database import get_db
from discovery.models import Challenge, Identity
from discovery.schemas import (
    AssertionPayload,
    IdentityPublic,
    ProfileUpdateRequest,
    PublishRequest,
    PublishResponse,
)
from discovery.services.symbol_derive import derive_symbol, public_key_id
from discovery.services.webauthn_verify import (
    AssertionError as WebAuthnAssertionError,
    verify_assertion,
)

router = APIRouter(tags=["publish"])


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _b64url_decode(s: str) -> bytes:
    s = s.replace("-", "+").replace("_", "/")
    pad = (4 - len(s) % 4) % 4
    return base64.b64decode(s + "=" * pad)


def _consume_challenge(token: str, db: Session) -> None:
    """Assert challenge is valid and unexpired, then delete it (single-use)."""
    challenge = db.get(Challenge, token)
    if challenge is None:
        raise HTTPException(422, "Invalid or unknown challenge token")
    if challenge.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        db.delete(challenge)
        db.commit()
        raise HTTPException(422, "Challenge token has expired — request a new one from GET /challenge")
    db.delete(challenge)
    db.commit()


def _assert_ownership(
    public_key_spki_b64url: str,
    assertion: AssertionPayload,
    challenge_token: str,
    origin: str,
) -> None:
    """Run WebAuthn assertion verification; raise HTTP 401 on failure."""
    try:
        verify_assertion(
            public_key_spki_b64url    = public_key_spki_b64url,
            client_data_json_b64url   = assertion.client_data_json,
            authenticator_data_b64url = assertion.authenticator_data,
            signature_b64url          = assertion.signature,
            expected_challenge_hex    = challenge_token,
            expected_origin           = origin,
            verify_origin             = settings.WEBAUTHN_VERIFY_ORIGIN,
        )
    except WebAuthnAssertionError as exc:
        raise HTTPException(401, f"Assertion verification failed: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# POST /publish
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/publish", response_model=PublishResponse, status_code=201)
def publish_identity(body: PublishRequest, db: Session = Depends(get_db)) -> PublishResponse:
    """
    Publish a new identity to this discovery server.

    Steps (all must pass):
    1. Decode public key bytes from base64url SPKI.
    2. Re-derive symbol_id/alias from the public key — must match submitted values.
    3. Consume the challenge token (single use, not expired).
    4. Verify the WebAuthn assertion.
    5. UPSERT identity (keyed on public_key_id).
    """

    # 1. Decode public key
    try:
        spki_bytes = _b64url_decode(body.public_key_spki)
    except Exception:
        raise HTTPException(422, "public_key_spki is not valid base64url")

    # 2. Symbol derivation integrity check
    derived_symbol, derived_alias = derive_symbol(spki_bytes)
    if derived_symbol != body.symbol_id:
        raise HTTPException(
            422,
            f"symbol_id mismatch: submitted {body.symbol_id!r} "
            f"but public key derives to {derived_symbol!r}",
        )
    if derived_alias != body.alias:
        raise HTTPException(
            422,
            f"alias mismatch: submitted {body.alias!r} "
            f"but public key derives to {derived_alias!r}",
        )

    # 3. Consume challenge (deletes token; do before assertion so it can't be replayed)
    _consume_challenge(body.challenge_token, db)

    # 4. Verify assertion (uses the token hex string — no DB lookup needed here)
    _assert_ownership(body.public_key_spki, body.assertion, body.challenge_token, body.origin)

    # 5. Upsert
    pk_id    = public_key_id(spki_bytes)
    existing = db.get(Identity, pk_id)

    if existing:
        existing.public_profile = body.public_profile
        existing.credential_id  = body.assertion.credential_id
        existing.updated_at     = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        row = existing
    else:
        row = Identity(
            public_key_id   = pk_id,
            symbol_id       = body.symbol_id,
            alias           = body.alias,
            public_key_spki = body.public_key_spki,
            origin          = body.origin,
            public_profile  = body.public_profile,
            credential_id   = body.assertion.credential_id,
        )
        try:
            db.add(row)
            db.commit()
            db.refresh(row)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                409,
                f"symbol_id {body.symbol_id!r} is already claimed by a different key. "
                "Symbol collision probability is ~1 in 156 billion — "
                "this is almost certainly a bug; contact the server operator.",
            )

    return PublishResponse(
        public_key_id = row.public_key_id,
        symbol_id     = row.symbol_id,
        alias         = row.alias,
        published_at  = row.published_at,
        updated_at    = row.updated_at,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PUT /profile
# ─────────────────────────────────────────────────────────────────────────────

@router.put("/profile", response_model=IdentityPublic)
def update_profile(body: ProfileUpdateRequest, db: Session = Depends(get_db)) -> IdentityPublic:
    """
    Update the public_profile of an existing identity.
    Caller must prove ownership via a fresh WebAuthn assertion.
    """
    identity = db.query(Identity).filter(Identity.symbol_id == body.symbol_id).first()
    if identity is None:
        raise HTTPException(404, f"Symbol {body.symbol_id!r} not found on this server")

    _consume_challenge(body.challenge_token, db)
    _assert_ownership(identity.public_key_spki, body.assertion, body.challenge_token, body.origin)

    identity.public_profile = body.public_profile
    identity.updated_at     = datetime.now(timezone.utc)
    db.commit()
    db.refresh(identity)
    return identity
