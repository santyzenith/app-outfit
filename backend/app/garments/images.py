import io

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
PHOTO_MAX_SIDE = 1600
CATALOG_SIDE = 1024

# The background level is read from the darkest 5% of the image border.
BACKGROUND_PERCENTILE = 0.05
MIN_BACKGROUND_LEVEL = 240


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


def _border_level(image: Image.Image, percentile: float) -> int:
    width, height = image.size
    strip = max(2, min(width, height) // 100)
    boxes = [
        (0, 0, width, strip),
        (0, height - strip, width, height),
        (0, 0, strip, height),
        (width - strip, 0, width, height),
    ]
    counts = [0] * 256
    for box in boxes:
        for level, count in enumerate(image.crop(box).convert("L").histogram()):
            counts[level] += count

    target = sum(counts) * percentile
    seen = 0
    for level, count in enumerate(counts):
        seen += count
        if seen >= target:
            return level
    return 255


def _whiten_background(image: Image.Image) -> Image.Image:
    # Models return an almost-white background; on a white screen that shows as a faint box.
    background = _border_level(image, BACKGROUND_PERCENTILE)
    if background < MIN_BACKGROUND_LEVEL:
        # The garment reaches the edges, so there is no clean background to measure.
        return image
    # Stretching the levels keeps soft shadows smooth, unlike cutting at a threshold.
    return image.point(lambda value: min(255, round(value * 255 / background)))


def normalize_catalog_image(data: bytes) -> bytes:
    return _to_jpeg(_whiten_background(_open(data)), CATALOG_SIDE)
