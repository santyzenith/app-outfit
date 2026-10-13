import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.schemas import ForecastOut, GarmentOut, OutfitOut
from app.auth.deps import CurrentUser, DbSession
from app.models import Garment, Occasion, Outfit
from app.outfits import service
from app.outfits.weather import Forecast, get_forecast

router = APIRouter(prefix="/outfits", tags=["outfits"])

Latitude = Annotated[float | None, Query(ge=-90, le=90)]
Longitude = Annotated[float | None, Query(ge=-180, le=180)]


def _forecast(day: dt.date, lat: float | None, lon: float | None) -> Forecast | None:
    if lat is None or lon is None:
        return None
    return get_forecast(lat, lon, day)


def _outfit_out(db: Session, outfit: Outfit, forecast: Forecast | None) -> OutfitOut:
    garments = {}
    for category, garment_id in outfit.garment_ids().items():
        garment = db.get(Garment, garment_id) if garment_id else None
        garments[category.value] = GarmentOut.model_validate(garment) if garment else None
    return OutfitOut(
        id=outfit.id,
        day=outfit.day,
        occasion=outfit.occasion,
        explanation=outfit.explanation,
        worn=outfit.worn_at is not None,
        garments=garments,
        forecast=ForecastOut.model_validate(forecast) if forecast else None,
    )


def _owned_outfit(outfit_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Outfit:
    try:
        return service.get_for_user(db, user, outfit_id)
    except service.OutfitNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "outfit_not_found") from exc


OwnedOutfit = Annotated[Outfit, Depends(_owned_outfit)]


@router.get("/today")
def read_today(
    day: dt.date,
    occasion: Occasion,
    user: CurrentUser,
    db: DbSession,
    lat: Latitude = None,
    lon: Longitude = None,
) -> OutfitOut:
    forecast = _forecast(day, lat, lon)
    try:
        outfit = service.get_today(db, user, day, occasion, forecast)
    except service.NotEnoughGarmentsError as exc:
        missing = [category.value for category in exc.missing]
        raise HTTPException(
            status.HTTP_409_CONFLICT, {"code": "not_enough_garments", "missing": missing}
        ) from exc
    return _outfit_out(db, outfit, forecast)


@router.get("/history")
def read_history(
    user: CurrentUser, db: DbSession, limit: Annotated[int, Query(ge=1, le=100)] = 30
) -> list[OutfitOut]:
    return [_outfit_out(db, outfit, None) for outfit in service.list_worn(db, user, limit)]


@router.post("/{outfit_id}/another")
def suggest_another(
    outfit: OwnedOutfit,
    user: CurrentUser,
    db: DbSession,
    lat: Latitude = None,
    lon: Longitude = None,
) -> OutfitOut:
    forecast = _forecast(outfit.day, lat, lon)
    try:
        replacement = service.another(db, user, outfit, forecast)
    except (service.NoMoreOutfitsError, service.NotEnoughGarmentsError) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "no_more_outfits"}) from exc
    return _outfit_out(db, replacement, forecast)


@router.post("/{outfit_id}/wear")
def wear_outfit(
    outfit: OwnedOutfit, db: DbSession, lat: Latitude = None, lon: Longitude = None
) -> OutfitOut:
    return _outfit_out(db, service.wear(db, outfit), _forecast(outfit.day, lat, lon))
