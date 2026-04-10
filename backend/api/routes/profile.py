"""Profile routes: GET/PUT /profile, GET /profile/{symbol_id} (public)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.user import User
from backend.models.identity import Identity
from backend.models.profile import Profile
from backend.schemas.profile import ProfileUpdate, ProfileOut, PublicProfileOut
from backend.api.deps import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


def _ensure_profile(user: User, db: Session) -> Profile:
    """Get or create a profile row for the user."""
    if user.profile:
        return user.profile
    profile = Profile(user_id=user.id, data={}, visibility={})
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/me", response_model=ProfileOut)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _ensure_profile(current_user, db)
    return profile


@router.put("/me", response_model=ProfileOut)
def update_my_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _ensure_profile(current_user, db)
    profile.data = body.data
    profile.visibility = body.visibility
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/{symbol_id}", response_model=PublicProfileOut)
def get_public_profile(symbol_id: str, db: Session = Depends(get_db)):
    """Return only the fields marked as 'public'."""
    identity = db.query(Identity).filter(Identity.symbol_id == symbol_id).first()
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found")

    user = identity.user
    profile = user.profile

    if not profile:
        public_data = {}
    else:
        public_data = {
            k: v
            for k, v in profile.data.items()
            if profile.visibility.get(k) == "public"
        }

    return PublicProfileOut(
        symbol_id=identity.symbol_id,
        alias=identity.alias,
        data=public_data,
    )
