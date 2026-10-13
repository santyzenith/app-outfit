import uuid

from sqlalchemy.orm import Session

from app import jobs
from app.ai.garments import analizar_prenda, recrear_prenda
from app.garments.images import normalize_catalog_image
from app.garments.service import PROCESS_JOB
from app.models import Garment, GarmentStatus
from app.storage import get_storage

NOT_A_GARMENT = "not_a_garment"
PROCESSING_ERROR = "processing_error"


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

    analysis = analizar_prenda(photo)
    if not analysis.is_garment:
        garment.status = GarmentStatus.FAILED
        garment.failure_reason = NOT_A_GARMENT
        return

    catalog_image = normalize_catalog_image(recrear_prenda(photo))
    garment.image_path = storage.save(garment.user_id, f"{garment.id}_catalog.jpg", catalog_image)
    garment.category = analysis.category
    garment.name = analysis.name
    garment.color = analysis.color
    garment.warmth = analysis.warmth
    garment.formality = analysis.formality
    garment.status = GarmentStatus.READY


def mark_failed(db: Session, payload: jobs.Payload) -> None:
    garment = _pending_garment(db, payload)
    if garment is not None:
        garment.status = GarmentStatus.FAILED
        garment.failure_reason = PROCESSING_ERROR


jobs.register(PROCESS_JOB, jobs.JobHandler(run=process_garment, on_give_up=mark_failed))
