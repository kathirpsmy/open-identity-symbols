"""Pydantic schemas for auth endpoints."""

from pydantic import BaseModel, EmailStr, field_validator
import re


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v


class RegisterResponse(BaseModel):
    message: str
    totp_qr: str          # base64 PNG data-URI
    totp_secret: str      # raw secret so user can also type it in manually


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ConfirmTOTPRequest(BaseModel):
    email: EmailStr
    totp_code: str
