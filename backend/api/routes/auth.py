"""Auth routes: /register, /login, /confirm-totp, /totp/reset, /me."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import (
    hash_password, verify_password,
    generate_totp_secret, totp_qr_base64, verify_totp,
    create_access_token,
)
from backend.models.user import User
from backend.schemas.auth import (
    RegisterRequest, RegisterResponse,
    LoginRequest, TokenResponse, ConfirmTOTPRequest,
    TOTPResetResponse, UserMeResponse,
)
from backend.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    secret = generate_totp_secret()
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        totp_secret=secret,
        totp_confirmed=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return RegisterResponse(
        message="Registration successful. Scan the QR code with your TOTP app.",
        totp_qr=totp_qr_base64(secret, body.email),
        totp_secret=secret,
    )


@router.post("/confirm-totp", response_model=TokenResponse)
def confirm_totp(body: ConfirmTOTPRequest, db: Session = Depends(get_db)):
    """Called after registration — verifies TOTP is set up correctly and issues a token."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or user.totp_confirmed:
        raise HTTPException(status_code=400, detail="Invalid request")
    if not verify_totp(user.totp_secret, body.totp_code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    user.totp_confirmed = True
    db.commit()
    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.totp_confirmed:
        raise HTTPException(status_code=403, detail="TOTP not confirmed — complete registration first")
    if not verify_totp(user.totp_secret, body.totp_code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")
    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token)


@router.post("/totp/reset", response_model=TOTPResetResponse)
def reset_totp(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reset TOTP for the authenticated user.

    Generates a fresh TOTP secret and marks the account as unconfirmed.
    The client must call POST /auth/confirm-totp to re-confirm with the new
    authenticator app entry before the next login.
    """
    new_secret = generate_totp_secret()
    current_user.totp_secret = new_secret
    current_user.totp_confirmed = False
    db.commit()
    return TOTPResetResponse(
        message="TOTP has been reset. Scan the new QR code with your authenticator app, then confirm with POST /auth/confirm-totp.",
        totp_qr=totp_qr_base64(new_secret, current_user.email),
        totp_secret=new_secret,
    )


@router.get("/me", response_model=UserMeResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return basic info about the authenticated user (email, admin status)."""
    return UserMeResponse(
        email=current_user.email,
        is_admin=current_user.is_admin,
        is_active=current_user.is_active,
    )
