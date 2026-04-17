"""
GET /search — case-insensitive substring search across symbol_id and alias.

Parameters
──────────
q       Search query (required).  Matched against symbol_id and alias with ILIKE.
limit   Max results to return (default 20, max 100).
offset  Pagination offset (default 0).

Example
───────
GET /search?q=fire&limit=5
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from discovery.database import get_db
from discovery.models import Identity
from discovery.schemas import SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search_identities(
    q: str     = Query(..., min_length=1, max_length=100, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """
    Case-insensitive substring search on symbol_id and alias.

    Returns paginated results with a `total` count for the full result set.
    """
    pattern = f"%{q}%"
    base_query = db.query(Identity).filter(
        or_(
            Identity.symbol_id.ilike(pattern),
            Identity.alias.ilike(pattern),
        )
    )
    total   = base_query.count()
    results = base_query.order_by(Identity.published_at.desc()).offset(offset).limit(limit).all()

    return SearchResponse(
        results = results,
        total   = total,
        limit   = limit,
        offset  = offset,
    )
