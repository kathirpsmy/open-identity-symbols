"""
Admin API — protected by ADMIN_API_KEY bearer token.

GET    /admin/stats                  — registry analytics
GET    /admin/identities             — paginated identity list with optional search
DELETE /admin/identity/{symbol_id}   — hard delete by symbol_id
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from discovery.config import settings
from discovery.database import get_db
from discovery.models import Identity

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(authorization: str | None = Header(default=None)) -> None:
    if not settings.ADMIN_API_KEY:
        raise HTTPException(503, "Admin API not configured — set ADMIN_API_KEY on this server")
    if authorization != f"Bearer {settings.ADMIN_API_KEY}":
        raise HTTPException(401, "Unauthorized")


def _row_to_dict(row: Identity) -> dict:
    return {
        "public_key_id":   row.public_key_id,
        "symbol_id":       row.symbol_id,
        "alias":           row.alias,
        "public_key_spki": row.public_key_spki,
        "credential_id":   row.credential_id,
        "origin":          row.origin,
        "public_profile":  row.public_profile,
        "published_at":    row.published_at.isoformat() if row.published_at else None,
        "updated_at":      row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), _: None = Depends(_require_admin)) -> dict:
    """Return basic registry analytics."""
    now           = datetime.now(timezone.utc)
    today_start   = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days    = now - timedelta(days=7)
    thirty_days   = now - timedelta(days=30)

    total    = db.query(func.count(Identity.public_key_id)).scalar() or 0
    today    = (db.query(func.count(Identity.public_key_id))
                  .filter(Identity.published_at >= today_start).scalar() or 0)
    last_7d  = (db.query(func.count(Identity.public_key_id))
                  .filter(Identity.published_at >= seven_days).scalar() or 0)
    last_30d = (db.query(func.count(Identity.public_key_id))
                  .filter(Identity.published_at >= thirty_days).scalar() or 0)

    most_recent_row = (db.query(Identity.published_at)
                         .order_by(Identity.published_at.desc()).first())
    most_recent = most_recent_row[0].isoformat() if most_recent_row else None

    return {
        "total_identities":       total,
        "registrations_today":    today,
        "registrations_last_7d":  last_7d,
        "registrations_last_30d": last_30d,
        "most_recent":            most_recent,
    }


@router.get("/identities")
def list_identities(
    limit:  int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0,  ge=0),
    q:      str = Query(default=""),
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
) -> dict:
    """Return a paginated, optionally filtered list of all registered identities."""
    query = db.query(Identity)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            Identity.symbol_id.ilike(pattern) | Identity.alias.ilike(pattern)
        )
    total = query.count()
    rows  = query.order_by(Identity.published_at.desc()).offset(offset).limit(limit).all()
    return {
        "results": [_row_to_dict(r) for r in rows],
        "total":   total,
        "limit":   limit,
        "offset":  offset,
    }


@router.delete("/identity/{symbol_id}", status_code=204)
def admin_delete(
    symbol_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
) -> Response:
    """Hard-delete an identity by symbol_id. Admin-only."""
    identity = db.query(Identity).filter(Identity.symbol_id == symbol_id).first()
    if identity is None:
        raise HTTPException(404, f"Symbol {symbol_id!r} not found")
    db.delete(identity)
    db.commit()
    return Response(status_code=204)
