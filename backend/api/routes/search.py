"""Public search route: GET /search?q=..."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List

from backend.core.database import get_db
from backend.models.identity import Identity
from backend.schemas.profile import PublicProfileOut

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=List[PublicProfileOut])
def search(
    q: str = Query(..., min_length=1, max_length=100, description="Search by symbol_id or alias"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Search identities by symbol_id or alias (case-insensitive prefix match)."""
    term = q.strip().lower()
    results = (
        db.query(Identity)
        .filter(
            or_(
                Identity.symbol_id.ilike(f"%{term}%"),
                Identity.alias.ilike(f"%{term}%"),
            )
        )
        .limit(limit)
        .all()
    )

    output = []
    for identity in results:
        user = identity.user
        profile = user.profile if user else None
        if profile:
            public_data = {
                k: v
                for k, v in profile.data.items()
                if profile.visibility.get(k) == "public"
            }
        else:
            public_data = {}

        output.append(
            PublicProfileOut(
                symbol_id=identity.symbol_id,
                alias=identity.alias,
                data=public_data,
            )
        )

    return output
