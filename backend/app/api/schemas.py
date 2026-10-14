import datetime as dt
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import (
    Formality,
    GarmentCategory,
    GarmentStatus,
    InspirationStatus,
    Occasion,
    Warmth,
)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str | None
    display_name: str | None
    is_guest: bool


class SessionOut(BaseModel):
    user: UserOut
    access_token: str
    refresh_token: str
    expires_in: int


class IdTokenIn(BaseModel):
    id_token: str


class RefreshTokenIn(BaseModel):
    refresh_token: str


class GarmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: GarmentStatus
    failure_reason: str | None
    category: GarmentCategory | None
    name: str | None
    color: str | None
    warmth: Warmth | None
    formality: Formality | None
    image_version: str | None
    created_at: datetime


class GarmentUpdate(BaseModel):
    category: GarmentCategory | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    color: str | None = Field(default=None, min_length=1, max_length=60)
    warmth: Warmth | None = None
    formality: Formality | None = None


class ForecastOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    min_c: float
    max_c: float
    rain: bool


class OutfitOut(BaseModel):
    id: uuid.UUID
    day: dt.date
    occasion: Occasion
    explanation: str
    worn: bool
    # One entry per garment category; empty slots are null.
    garments: dict[str, GarmentOut | None]
    # Categories the closet could only fill with something off the occasion.
    off_occasion: list[str]
    forecast: ForecastOut | None


class MissingPieceOut(BaseModel):
    category: GarmentCategory
    name: str


class InspirationOut(BaseModel):
    id: uuid.UUID
    status: InspirationStatus
    failure_reason: str | None
    # The closet's stand-in for each piece of the look; empty slots are null.
    garments: dict[str, GarmentOut | None]
    missing: list[MissingPieceOut]
    explanation: str | None
    created_at: datetime
