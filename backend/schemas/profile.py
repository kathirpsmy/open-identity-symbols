"""Pydantic schemas for profile endpoints."""

from datetime import datetime
from typing import Dict, Any, Literal
from pydantic import BaseModel


VisibilityValue = Literal["public", "private"]


class ProfileUpdate(BaseModel):
    data: Dict[str, Any]
    visibility: Dict[str, VisibilityValue] = {}


class ProfileOut(BaseModel):
    data: Dict[str, Any]
    visibility: Dict[str, str]
    updated_at: datetime

    model_config = {"from_attributes": True}


class PublicProfileOut(BaseModel):
    """Only public fields are returned."""
    symbol_id: str
    alias: str
    data: Dict[str, Any]  # only public fields
