"""Profile model — stores user-editable profile data with field-level visibility."""

from datetime import datetime, timezone
from sqlalchemy import Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.core.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Flexible JSON fields so users can add any data
    data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Per-field visibility: {"display_name": "public", "bio": "private", ...}
    # Values: "public" | "private"
    visibility: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="profile")
