import io

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
PHOTO_MAX_SIDE = 1600
CATALOG_SIDE = 1024


class InvalidImageError(Exception):
    pass


def _open(data: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise InvalidImageError from exc
    # Phones store rotation as metadata; bake it in before the metadata is dropped.
    return ImageOps.exif_transpose(image).convert("RGB")


def _to_jpeg(image: Image.Image, max_side: int) -> bytes:
    image.thumbnail((max_side, max_side))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=88)
    return buffer.getvalue()


def normalize_photo(data: bytes) -> bytes:
    return _to_jpeg(_open(data), PHOTO_MAX_SIDE)


def normalize_catalog_image(data: bytes) -> bytes:
    return _to_jpeg(_open(data), CATALOG_SIDE)
