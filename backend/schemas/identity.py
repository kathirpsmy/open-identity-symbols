"""Pydantic schemas for identity endpoints."""

from datetime import datetime
from pydantic import BaseModel


class IdentityOut(BaseModel):
    symbol_id: str
    alias: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateIDResponse(BaseModel):
    symbol_id: str
    alias: str
    created_at: datetime

    model_config = {"from_attributes": True}
