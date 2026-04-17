"""
Discovery server database models.

Design notes for federation / mergeability
──────────────────────────────────────────
• `public_key_id` = SHA-256(SPKI bytes) hex — the globally unique merge key.
  When two discovery servers are merged, UPSERT on this column is idempotent.

• `symbol_id` has a UNIQUE constraint per-server.  Symbol collision (two
  different public keys hashing to the same triple) is statistically negligible
  (p ≈ 1 in 156 billion) but handled at the DB level: the second publisher
  receives a 409 Conflict and must contact the first publisher out-of-band.
  A future `/verify` endpoint resolves disputes by proof-of-key.

• `origin` records the WebAuthn RP origin the credential was created under.
  Needed to reconstruct the correct rpId for assertion verification on
  subsequent profile updates.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from discovery.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Identity(Base):
    __tablename__ = "identities"

    # True globally unique key — SHA-256(SPKI bytes) hex
    public_key_id: Mapped[str] = mapped_column(String(64), primary_key=True)

    # Human-readable identity — unique per server
    symbol_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    alias: Mapped[str]     = mapped_column(String(128), unique=True, nullable=False)

    # Public key storage (base64url SPKI DER)
    public_key_spki: Mapped[str] = mapped_column(Text, nullable=False)

    # WebAuthn credential ID (base64url).  Stored to enable cross-device recovery:
    # a user who has cleared local storage can re-authenticate via passkey, get
    # their credentialId back from the browser, and look up their identity here.
    # Nullable for backwards-compatibility with rows published before this column
    # was added.  Existing DBs need: ALTER TABLE identities ADD COLUMN credential_id VARCHAR(512);
    credential_id: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # WebAuthn origin this passkey was created under (e.g. "https://foo.github.io")
    # Used to reconstruct rp_id for subsequent assertion verification.
    origin: Mapped[str] = mapped_column(String(512), nullable=False)

    # User-controlled public profile (arbitrary JSON).
    # JSON maps to TEXT in SQLite (tests) and JSONB in PostgreSQL (production).
    public_profile: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    __table_args__ = (
        Index("ix_identities_symbol_id", "symbol_id"),
        Index("ix_identities_alias", "alias"),
        Index("ix_identities_credential_id", "credential_id"),
    )


class Challenge(Base):
    """
    One-time challenges issued to clients before they sign an assertion.
    The PWA requests a token, uses it as the WebAuthn challenge, then submits
    it alongside the assertion. Tokens are deleted on use or expiry.
    """
    __tablename__ = "challenges"

    token: Mapped[str]     = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
