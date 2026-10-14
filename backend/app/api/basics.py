from typing import Literal

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.api.schemas import BasicColorOut, BasicOut, BasicsIn, GarmentOut
from app.auth.deps import CurrentUser, DbSession
from app.garments import basics
from app.garments.service import thumbnail
from app.storage import get_storage

router = APIRouter(prefix="/basics", tags=["basics"])


@router.get("")
def list_basics(user: CurrentUser, db: DbSession) -> list[BasicOut]:
    owned = basics.owned_keys(db, user)
    return [
        BasicOut(
            key=shape.key,
            name=shape.name,
            category=shape.category,
            colors=[
                BasicColorOut(
                    key=color.key,
                    name=color.forms[basics.GENDER_INDEX[shape.gender]],
                    swatch=color.swatch,
                    owned=basics.basic_key(shape, color) in owned,
                )
                for color in (basics.COLORS[key] for key in shape.colors)
            ],
        )
        for shape in basics.available()
    ]


@router.get("/{shape_key}/image")
def read_basic_image(
    shape_key: str, color: str, user: CurrentUser, size: Literal["full", "thumb"] = "full"
) -> FileResponse:
    try:
        shape, paint = basics.parse_key(f"{shape_key}:{color}")
    except basics.UnknownBasicError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "basic_not_found") from exc
    if shape not in basics.available():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "basic_not_found")
    storage = get_storage()
    path = basics.image_path(storage, shape, paint)
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
