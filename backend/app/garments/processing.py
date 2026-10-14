import uuid

from sqlalchemy.orm import Session

from app import jobs
from app.ai.garments import GarmentAnalysis, analizar_prenda, recrear_prenda
from app.garments.images import normalize_catalog_image, thumbnail_path
from app.garments.service import PROCESS_JOB, create_from_shared_photo, describe
from app.models import Garment, GarmentStatus
from app.storage import get_storage

NOT_A_GARMENT = "not_a_garment"
PROCESSING_ERROR = "processing_error"
# Caps what one photo can cost: every item is a paid image generation.
MAX_ITEMS_PER_PHOTO = 6


def _pending_garment(db: Session, payload: jobs.Payload) -> Garment | None:
    garment = db.get(Garment, uuid.UUID(payload["garment_id"]))
    if garment is None or garment.status != GarmentStatus.PROCESSING:
        return None
    return garment


def process_garment(db: Session, payload: jobs.Payload) -> None:
    garment = _pending_garment(db, payload)
    if garment is None:
        return

    storage = get_storage()
    photo = storage.read(garment.original_path)

    # A garment split from a shared photo was already analysed with the rest of that photo.
    others: list[GarmentAnalysis] = []
    if garment.focus is None:
        items = analizar_prenda(photo)[:MAX_ITEMS_PER_PHOTO]
        if not items:
            garment.status = GarmentStatus.FAILED
            garment.failure_reason = NOT_A_GARMENT
            return
        first, *others = items
        describe(garment, first)
        if others:
            garment.focus = first.description

    catalog_image = normalize_catalog_image(recrear_prenda(photo, garment.focus))
    previous_image = garment.image_path
    # A new file name each time, so phones never show a cached older version.
    filename = f"{garment.id}_catalog_{uuid.uuid4().hex[:8]}.jpg"
    garment.image_path = storage.save(garment.user_id, filename, catalog_image)
    if previous_image:
        storage.delete(previous_image)
        storage.delete(thumbnail_path(previous_image))
    garment.status = GarmentStatus.READY
    for item in others:
        create_from_shared_photo(db, storage, garment, item)


def mark_failed(db: Session, payload: jobs.Payload) -> None:
    garment = _pending_garment(db, payload)
    if garment is not None:
        garment.status = GarmentStatus.FAILED
        garment.failure_reason = PROCESSING_ERROR


jobs.register(PROCESS_JOB, jobs.JobHandler(run=process_garment, on_give_up=mark_failed))
