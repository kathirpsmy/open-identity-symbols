"""Admin routes — user management and analytics.

All endpoints require an authenticated admin user.
"""

from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api.deps import get_current_admin, get_db
from backend.models.user import User
from backend.models.identity import Identity
from backend.schemas.admin import UserAdminOut, AnalyticsOut

router = APIRouter(prefix="/admin", tags=["admin"])


def _user_to_out(user: User) -> UserAdminOut:
    return UserAdminOut(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        totp_confirmed=user.totp_confirmed,
        has_identity=user.identity is not None,
        created_at=user.created_at,
    )


@router.get("/users", response_model=List[UserAdminOut])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Return a paginated list of all users."""
    users = db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return [_user_to_out(u) for u in users]


@router.patch("/users/{user_id}/deactivate", response_model=UserAdminOut)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Deactivate a user account (blocks login and all authenticated requests)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Admins cannot deactivate their own account")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return _user_to_out(user)


@router.patch("/users/{user_id}/activate", response_model=UserAdminOut)
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Re-activate a previously deactivated user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    db.commit()
    db.refresh(user)
    return _user_to_out(user)


@router.get("/analytics", response_model=AnalyticsOut)
def get_analytics(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Return aggregate platform statistics."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()  # noqa: E712
    inactive_users = total_users - active_users
    admin_users = db.query(User).filter(User.is_admin == True).count()  # noqa: E712
    total_identities = db.query(Identity).count()
    new_users_last_7_days = db.query(User).filter(User.created_at >= cutoff).count()

    return AnalyticsOut(
        total_users=total_users,
        active_users=active_users,
        inactive_users=inactive_users,
        admin_users=admin_users,
        total_identities=total_identities,
        new_users_last_7_days=new_users_last_7_days,
    )
