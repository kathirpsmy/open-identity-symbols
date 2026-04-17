"""
GET /challenge — issue a one-time challenge token.

The PWA calls this endpoint, receives a hex token, decodes it to bytes,
and passes those bytes as the `challenge` in navigator.credentials.get().
The token is stored in the DB with a TTL and deleted on use.
"""

import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import delete
from sqlalchemy.orm import Session

from discovery.config import settings
from discovery.database import get_db
from discovery.models import Challenge
from discovery.schemas import ChallengeResponse

router = APIRouter(prefix="/challenge", tags=["challenge"])


@router.get("", response_model=ChallengeResponse)
def get_challenge(db: Session = Depends(get_db)) -> ChallengeResponse:
    """
    Issue a one-time 32-byte challenge token.

    The client must use this token as the WebAuthn challenge within
    `CHALLENGE_TTL_SECONDS` (default 5 minutes).
    """
    # Purge expired tokens (best-effort housekeeping)
    db.execute(
        delete(Challenge).where(Challenge.expires_at < datetime.now(timezone.utc))
    )
    db.commit()

    token = os.urandom(32).hex()
    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=settings.CHALLENGE_TTL_SECONDS
    )
    db.add(Challenge(token=token, expires_at=expires_at))
    db.commit()

    return ChallengeResponse(token=token, expires_at=expires_at)
