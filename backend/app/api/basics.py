from typing import Literal

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.api.schemas import BasicOut, BasicsIn, GarmentOut
from app.auth.deps import CurrentUser, DbSession
from app.garments import basics
from app.garments.service import thumbnail
from app.storage import get_storage

router = APIRouter(prefix="/basics", tags=["basics"])


@router.get("")
def list_basics(user: CurrentUser, db: DbSession) -> list[BasicOut]:
    owned = basics.owned_keys(db, user)
    return [
        BasicOut(key=basic.key, name=basic.name, category=basic.category, owned=basic.key in owned)
        for basic in basics.available(get_storage())
    ]


@router.get("/{key}/image")
def read_basic_image(
    key: str, user: CurrentUser, size: Literal["full", "thumb"] = "full"
) -> FileResponse:
    storage = get_storage()
    basic = basics.BY_KEY.get(key)
    if basic is None or not storage.exists(basics.image_path(basic)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "basic_not_found")
    path = basics.image_path(basic)
    if size == "thumb":
        path = thumbnail(storage, path)
    return FileResponse(
        storage.path(path), media_type="image/jpeg", headers={"Cache-Control": "max-age=604800"}
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def add_basics(body: BasicsIn, user: CurrentUser, db: DbSession) -> list[GarmentOut]:
    try:
        garments = basics.add_to_closet(db, get_storage(), user, body.keys)
    except basics.UnknownBasicError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "unknown_basic") from exc
    return [GarmentOut.model_validate(garment) for garment in garments]
