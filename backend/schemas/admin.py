"""Pydantic schemas for admin endpoints."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class UserAdminOut(BaseModel):
    id: int
    email: str
    is_active: bool
    is_admin: bool
    totp_confirmed: bool
    has_identity: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsOut(BaseModel):
    total_users: int
    active_users: int
    inactive_users: int
    admin_users: int
    total_identities: int
    new_users_last_7_days: int
