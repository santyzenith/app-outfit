import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.outfits import Latitude, Longitude, _forecast, _not_enough_garments, _outfit_out
from app.api.schemas import GarmentOut, InspirationOut, MissingPieceOut, OutfitOut
from app.auth.deps import CurrentUser, DbSession
from app.garments.images import MAX_UPLOAD_BYTES, InvalidImageError
from app.inspirations import service
from app.models import Garment, Inspiration, InspirationStatus, Occasion
from app.outfits import service as outfit_service
from app.storage import get_storage

router = APIRouter(prefix="/inspirations", tags=["inspirations"])


def _inspiration_out(db: Session, inspiration: Inspiration) -> InspirationOut:
    garments = {}
    for category, garment_id in inspiration.garment_ids().items():
        garment = db.get(Garment, garment_id) if garment_id else None
        garments[category.value] = GarmentOut.model_validate(garment) if garment else None
    return InspirationOut(
        id=inspiration.id,
        status=inspiration.status,
        failure_reason=inspiration.failure_reason,
        garments=garments,
        missing=[MissingPieceOut(**piece) for piece in inspiration.missing or []],
        explanation=inspiration.explanation,
        created_at=inspiration.created_at,
    )


def _owned(inspiration_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Inspiration:
    try:
        return service.get_for_user(db, user, inspiration_id)
    except service.InspirationNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "inspiration_not_found") from exc


OwnedInspiration = Annotated[Inspiration, Depends(_owned)]


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def upload_inspiration(photo: UploadFile, user: CurrentUser, db: DbSession) -> InspirationOut:
    data = photo.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "photo_too_large")
    try:
        inspiration = service.create_from_photo(db, get_storage(), user, data)
    except InvalidImageError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_image") from exc
    except service.InspirationLimitError as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "inspiration_limit_reached") from exc
    return _inspiration_out(db, inspiration)


@router.get("")
def list_inspirations(user: CurrentUser, db: DbSession) -> list[InspirationOut]:
    return [_inspiration_out(db, item) for item in service.list_for_user(db, user)]


@router.get("/{inspiration_id}")
def read_inspiration(inspiration: OwnedInspiration, db: DbSession) -> InspirationOut:
    return _inspiration_out(db, inspiration)


@router.delete("/{inspiration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inspiration(inspiration: OwnedInspiration, db: DbSession) -> None:
    service.delete(db, get_storage(), inspiration)


@router.get("/{inspiration_id}/image")
def read_inspiration_image(inspiration: OwnedInspiration) -> FileResponse:
    return FileResponse(
        get_storage().path(inspiration.photo_path),
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.post("/{inspiration_id}/use")
def use_inspiration(
    inspiration: OwnedInspiration,
    day: dt.date,
    occasion: Occasion,
    user: CurrentUser,
    db: DbSession,
    lat: Latitude = None,
    lon: Longitude = None,
) -> OutfitOut:
    if inspiration.status != InspirationStatus.READY:
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "inspiration_not_ready"})
    forecast = _forecast(day, lat, lon)
    try:
        outfit = outfit_service.use_look(
            db,
            user,
            inspiration.garment_ids(),
            inspiration.explanation or "",
            day,
            occasion,
            forecast,
        )
    except outfit_service.NotEnoughGarmentsError as exc:
        raise _not_enough_garments(exc) from exc
    return _outfit_out(db, outfit, forecast)
