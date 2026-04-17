from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Challenge
# ─────────────────────────────────────────────────────────────────────────────

class ChallengeResponse(BaseModel):
    token: str = Field(description="Hex-encoded random challenge token (32 bytes = 64 hex chars)")
    expires_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# WebAuthn assertion (sent by the PWA)
# ─────────────────────────────────────────────────────────────────────────────

class AssertionPayload(BaseModel):
    credential_id: str    = Field(description="base64url credential ID")
    client_data_json: str = Field(description="base64url clientDataJSON bytes")
    authenticator_data: str = Field(description="base64url authenticatorData bytes")
    signature: str        = Field(description="base64url signature bytes")


# ─────────────────────────────────────────────────────────────────────────────
# Publish
# ─────────────────────────────────────────────────────────────────────────────

class PublishRequest(BaseModel):
    symbol_id: str       = Field(max_length=64)
    alias: str           = Field(max_length=128)
    public_key_spki: str = Field(description="base64url SPKI DER bytes of the credential public key")
    origin: str          = Field(
        description="WebAuthn origin the passkey was created under, e.g. 'https://foo.github.io'"
    )
    challenge_token: str = Field(description="Token from GET /challenge")
    assertion: AssertionPayload
    public_profile: dict[str, Any] | None = None

    @field_validator("origin")
    @classmethod
    def origin_must_be_https_or_localhost(cls, v: str) -> str:
        if not (v.startswith("https://") or v.startswith("http://localhost") or
                v.startswith("http://127.0.0.1")):
            raise ValueError("origin must be HTTPS or localhost")
        return v


class PublishResponse(BaseModel):
    public_key_id: str
    symbol_id: str
    alias: str
    published_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Profile update
# ─────────────────────────────────────────────────────────────────────────────

class ProfileUpdateRequest(BaseModel):
    symbol_id: str
    origin: str
    challenge_token: str
    assertion: AssertionPayload
    public_profile: dict[str, Any]

    @field_validator("origin")
    @classmethod
    def origin_must_be_https_or_localhost(cls, v: str) -> str:
        if not (v.startswith("https://") or v.startswith("http://localhost") or
                v.startswith("http://127.0.0.1")):
            raise ValueError("origin must be HTTPS or localhost")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# Identity (public view)
# ─────────────────────────────────────────────────────────────────────────────

class IdentityPublic(BaseModel):
    public_key_id: str
    symbol_id: str
    alias: str
    public_key_spki: str
    public_profile: dict[str, Any] | None
    published_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Search
# ─────────────────────────────────────────────────────────────────────────────

class SearchResponse(BaseModel):
    results: list[IdentityPublic]
    total: int
    limit: int
    offset: int
