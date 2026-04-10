"""Identity routes: /identity/generate, /identity/{symbol_id}."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.user import User
from backend.models.identity import Identity
from backend.schemas.identity import IdentityOut, GenerateIDResponse
from backend.services.identity_engine import generate_symbol_id
from backend.api.deps import get_current_user

router = APIRouter(prefix="/identity", tags=["identity"])

_MAX_RETRIES = 10


@router.post("/generate", response_model=GenerateIDResponse, status_code=status.HTTP_201_CREATED)
def generate_identity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a unique 3-symbol ID for the authenticated user."""
    if current_user.identity:
        raise HTTPException(status_code=409, detail="Identity already assigned to this user")

    for _ in range(_MAX_RETRIES):
        candidate = generate_symbol_id()
        exists = db.query(Identity).filter(
            Identity.symbol_id == candidate["symbol_id"]
        ).first()
        if not exists:
            identity = Identity(
                user_id=current_user.id,
                symbol_id=candidate["symbol_id"],
                alias=candidate["alias"],
            )
            db.add(identity)
            db.commit()
            db.refresh(identity)
            return identity

    raise HTTPException(
        status_code=503,
        detail="Could not generate a unique ID after retries. Please try again.",
    )


@router.get("/me", response_model=IdentityOut)
def get_my_identity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.identity:
        raise HTTPException(status_code=404, detail="No identity assigned yet")
    return current_user.identity


@router.get("/{symbol_id}", response_model=IdentityOut)
def get_identity_by_id(symbol_id: str, db: Session = Depends(get_db)):
    """Public lookup by symbol_id."""
    identity = db.query(Identity).filter(Identity.symbol_id == symbol_id).first()
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found")
    return identity
