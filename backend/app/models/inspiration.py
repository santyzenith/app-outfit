import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.garment import GarmentCategory, text_enum
from app.models.outfit import garment_slot


class InspirationStatus(enum.StrEnum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Inspiration(Base):
    # A reference look the user wants to recreate with the clothes they own.
    __tablename__ = "inspirations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[InspirationStatus] = mapped_column(
        text_enum(InspirationStatus), default=InspirationStatus.PROCESSING
    )
    failure_reason: Mapped[str | None] = mapped_column(String(50))
    photo_path: Mapped[str] = mapped_column(String(255))

    top_id: Mapped[uuid.UUID | None] = garment_slot()
    bottom_id: Mapped[uuid.UUID | None] = garment_slot()
    one_piece_id: Mapped[uuid.UUID | None] = garment_slot()
    outerwear_id: Mapped[uuid.UUID | None] = garment_slot()
    shoes_id: Mapped[uuid.UUID | None] = garment_slot()
    accessory_id: Mapped[uuid.UUID | None] = garment_slot()

    # Pieces of the look the closet has nothing close to: [{"category", "name"}].
    missing: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    explanation: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def garment_ids(self) -> dict[GarmentCategory, uuid.UUID | None]:
        return {category: getattr(self, f"{category.value}_id") for category in GarmentCategory}
