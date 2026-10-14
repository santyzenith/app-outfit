import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.schemas import GarmentOut, GarmentUpdate
from app.auth.deps import CurrentUser, DbSession
from app.garments import service
from app.garments.images import MAX_UPLOAD_BYTES, InvalidImageError
from app.models import Garment, GarmentStatus
from app.storage import get_storage

router = APIRouter(prefix="/garments", tags=["garments"])


def _owned_garment(garment_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Garment:
    try:
        return service.get_for_user(db, user, garment_id)
    except service.GarmentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "garment_not_found") from exc


OwnedGarment = Annotated[Garment, Depends(_owned_garment)]


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def upload_garment(photo: UploadFile, user: CurrentUser, db: DbSession) -> GarmentOut:
    data = photo.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "photo_too_large")
    try:
        garment = service.create_from_photo(db, get_storage(), user, data)
    except InvalidImageError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_image") from exc
    except service.UploadLimitError as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "upload_limit_reached") from exc
    return GarmentOut.model_validate(garment)


@router.get("")
def list_garments(
    user: CurrentUser, db: DbSession, status: GarmentStatus | None = None
) -> list[GarmentOut]:
    garments = service.list_for_user(db, user, status)
    return [GarmentOut.model_validate(garment) for garment in garments]


@router.get("/{garment_id}")
def read_garment(garment: OwnedGarment) -> GarmentOut:
    return GarmentOut.model_validate(garment)


@router.patch("/{garment_id}")
def update_garment(garment: OwnedGarment, body: GarmentUpdate, db: DbSession) -> GarmentOut:
    changes = body.model_dump(exclude_none=True)
    return GarmentOut.model_validate(service.update(db, garment, changes))


@router.post("/{garment_id}/retry", status_code=status.HTTP_202_ACCEPTED)
def retry_garment(garment: OwnedGarment, db: DbSession) -> GarmentOut:
    try:
        return GarmentOut.model_validate(service.retry(db, garment))
    except service.GarmentNotRetryableError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "garment_not_failed") from exc


@router.delete("/{garment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_garment(garment: OwnedGarment, db: DbSession) -> None:
    service.delete(db, get_storage(), garment)


@router.get("/{garment_id}/image")
def read_garment_image(
    garment: OwnedGarment,
    variant: Literal["catalog", "original"] = "catalog",
    size: Literal["full", "thumb"] = "full",
) -> FileResponse:
    relative_path = garment.image_path if variant == "catalog" else garment.original_path
    if relative_path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "image_not_ready")
    storage = get_storage()
    if size == "thumb":
        relative_path = service.thumbnail(storage, relative_path)
    return FileResponse(
        storage.path(relative_path),
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=86400"},
    )
