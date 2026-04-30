"""
DELETE /identity — user self-delete via WebAuthn assertion.

No admin key required. Caller proves ownership of the identity by signing
a challenge with the same passkey used at publish time.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from discovery.config import settings
from discovery.database import get_db
from discovery.models import Identity
from discovery.schemas import AssertionPayload
from discovery.api.publish import _assert_ownership, _consume_challenge

router = APIRouter(tags=["identity"])


class SelfDeleteRequest(BaseModel):
    symbol_id: str
    challenge_token: str
    assertion: AssertionPayload


@router.delete("/identity", status_code=204)
def self_delete(body: SelfDeleteRequest, db: Session = Depends(get_db)) -> Response:
    """
    Hard-delete the caller's identity from this discovery server.

    Requires a valid WebAuthn assertion proving ownership of the registered
    passkey. Uses the origin stored at publish time as the expected RP origin.
    """
    identity = db.query(Identity).filter(Identity.symbol_id == body.symbol_id).first()
    if identity is None:
        raise HTTPException(404, f"Symbol {body.symbol_id!r} not found on this server")

    _consume_challenge(body.challenge_token, db)
    _assert_ownership(identity.public_key_spki, body.assertion, body.challenge_token, identity.origin)

    db.delete(identity)
    db.commit()
    return Response(status_code=204)
