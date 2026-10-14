import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import jobs
from app.ai.inspirations import extraer_estilo
from app.inspirations.service import MATCH_JOB
from app.models import Garment, GarmentStatus, Inspiration, InspirationStatus
from app.storage import get_storage

NOT_A_LOOK = "not_a_look"
PROCESSING_ERROR = "processing_error"


def _pending(db: Session, payload: jobs.Payload) -> Inspiration | None:
    inspiration = db.get(Inspiration, uuid.UUID(payload["inspiration_id"]))
    if inspiration is None or inspiration.status != InspirationStatus.PROCESSING:
        return None
    return inspiration


def match_inspiration(db: Session, payload: jobs.Payload) -> None:
    inspiration = _pending(db, payload)
    if inspiration is None:
        return
    closet = list(
        db.scalars(
            select(Garment).where(
                Garment.user_id == inspiration.user_id, Garment.status == GarmentStatus.READY
            )
        )
    )
    match = extraer_estilo(get_storage().read(inspiration.photo_path), closet)
    if not match.is_look:
        inspiration.status = InspirationStatus.FAILED
        inspiration.failure_reason = NOT_A_LOOK
        return
    for category, garment_id in match.garment_ids.items():
        setattr(inspiration, f"{category.value}_id", garment_id)
    inspiration.missing = [
        {"category": piece.category.value, "name": piece.name} for piece in match.missing
    ]
    inspiration.explanation = match.explanation
    inspiration.status = InspirationStatus.READY


def mark_failed(db: Session, payload: jobs.Payload) -> None:
    inspiration = _pending(db, payload)
    if inspiration is not None:
        inspiration.status = InspirationStatus.FAILED
        inspiration.failure_reason = PROCESSING_ERROR


jobs.register(MATCH_JOB, jobs.JobHandler(run=match_inspiration, on_give_up=mark_failed))
