import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.openrouter import AIError
from app.ai.outfits import OutfitChoice, sugerir_outfits
from app.models import Garment, GarmentCategory, GarmentStatus, Occasion, Outfit, User
from app.outfits.candidates import Candidates, select_candidates
from app.outfits.weather import Forecast

# Outfits generated per model call: today's pick plus ready-made answers to "otra".
BATCH_SIZE = 3
FALLBACK_EXPLANATION = "Una combinación sencilla con prendas que no has usado últimamente."

Combo = frozenset[uuid.UUID]


class NotEnoughGarmentsError(Exception):
    def __init__(self, missing: list[GarmentCategory]) -> None:
        self.missing = missing


class NoMoreOutfitsError(Exception):
    pass


class OutfitNotFoundError(Exception):
    pass


class GarmentNotReadyError(Exception):
    pass


def _combo(garment_ids: dict[GarmentCategory, uuid.UUID | None]) -> Combo:
    return frozenset(garment_id for garment_id in garment_ids.values() if garment_id)


def _is_wearable(choice: OutfitChoice) -> bool:
    ids = choice.garment_ids
    separates = bool(ids[GarmentCategory.TOP] and ids[GarmentCategory.BOTTOM])
    one_piece = bool(ids[GarmentCategory.ONE_PIECE])
    mixes_both = one_piece and bool(ids[GarmentCategory.TOP] or ids[GarmentCategory.BOTTOM])
    return (separates or one_piece) and not mixes_both and bool(ids[GarmentCategory.SHOES])


def _fallback_choice(candidates: Candidates) -> OutfitChoice:
    # Used when the model is unavailable: the least recently worn garment of each slot.
    first = {
        category: garments[0].id if garments else None
        for category, garments in candidates.by_category.items()
    }
    if first[GarmentCategory.TOP] and first[GarmentCategory.BOTTOM]:
        first[GarmentCategory.ONE_PIECE] = None
    else:
        first[GarmentCategory.TOP] = first[GarmentCategory.BOTTOM] = None
    if not candidates.wants_outerwear:
        first[GarmentCategory.OUTERWEAR] = None
    first[GarmentCategory.ACCESSORY] = None
    return OutfitChoice(first, FALLBACK_EXPLANATION)


def _for_day(db: Session, user: User, day: dt.date, occasion: Occasion) -> list[Outfit]:
    return list(
        db.scalars(
            select(Outfit)
            .where(Outfit.user_id == user.id, Outfit.day == day, Outfit.occasion == occasion)
            .order_by(Outfit.position)
        )
    )


def _is_available(outfit: Outfit) -> bool:
    return outfit.dismissed_at is None and outfit.is_complete


def _generate(
    db: Session,
    user: User,
    day: dt.date,
    occasion: Occasion,
    forecast: Forecast | None,
    existing: list[Outfit],
    around: Garment | None = None,
) -> list[Outfit]:
    garments = list(
        db.scalars(
            select(Garment).where(Garment.user_id == user.id, Garment.status == GarmentStatus.READY)
        )
    )
    candidates = select_candidates(garments, occasion, forecast, day)
    if around is not None:
        candidates = candidates.built_around(around)
    if candidates.missing:
        raise NotEnoughGarmentsError(candidates.missing)

    seen = {_combo(outfit.garment_ids()) for outfit in existing}
    try:
        choices = sugerir_outfits(candidates, occasion, forecast, list(seen), BATCH_SIZE)
    except AIError:
        choices = []
    if not existing or around is not None:
        # The first outfit of the day, or one asked for, must never fail because of the model.
        choices.append(_fallback_choice(candidates))

    outfits = []
    for choice in choices:
        combo = _combo(choice.garment_ids)
        if not _is_wearable(choice) or combo in seen:
            continue
        seen.add(combo)
        slots = {f"{category.value}_id": gid for category, gid in choice.garment_ids.items()}
        outfits.append(
            Outfit(
                user_id=user.id,
                day=day,
                occasion=occasion,
                position=len(existing) + len(outfits),
                explanation=choice.explanation or FALLBACK_EXPLANATION,
                **slots,
            )
        )
    if not outfits:
        raise NoMoreOutfitsError

    db.add_all(outfits)
    db.commit()
    return outfits


def remember_context(
    db: Session, user: User, lat: float | None, lon: float | None, utc_offset_minutes: int | None
) -> None:
    user.last_seen_at = dt.datetime.now(dt.UTC)
    if lat is not None and lon is not None:
        user.latitude, user.longitude = lat, lon
    if utc_offset_minutes is not None:
        user.utc_offset_minutes = utc_offset_minutes
    db.commit()


def get_today(
    db: Session, user: User, day: dt.date, occasion: Occasion, forecast: Forecast | None
) -> Outfit:
    existing = _for_day(db, user, day, occasion)
    for outfit in existing:
        if _is_available(outfit):
            return outfit
    return _generate(db, user, day, occasion, forecast, existing)[0]


def build_around(
    db: Session,
    user: User,
    garment: Garment,
    day: dt.date,
    occasion: Occasion,
    forecast: Forecast | None,
) -> Outfit:
    if garment.status != GarmentStatus.READY:
        raise GarmentNotReadyError
    existing = _for_day(db, user, day, occasion)
    outfits = _generate(db, user, day, occasion, forecast, existing, around=garment)
    # What was on screen steps aside so the requested outfit is the one shown.
    now = dt.datetime.now(dt.UTC)
    for outfit in existing:
        if outfit.dismissed_at is None:
            outfit.dismissed_at = now
    db.commit()
    return outfits[0]


def list_worn(db: Session, user: User, limit: int) -> list[Outfit]:
    return list(
        db.scalars(
            select(Outfit)
            .where(Outfit.user_id == user.id, Outfit.worn_at.is_not(None))
            .order_by(Outfit.worn_at.desc())
            .limit(limit)
        )
    )


def get_for_user(db: Session, user: User, outfit_id: uuid.UUID) -> Outfit:
    outfit = db.get(Outfit, outfit_id)
    if outfit is None or outfit.user_id != user.id:
        raise OutfitNotFoundError
    return outfit


def another(db: Session, user: User, outfit: Outfit, forecast: Forecast | None) -> Outfit:
    existing = _for_day(db, user, outfit.day, outfit.occasion)
    ready = [other for other in existing if other.id != outfit.id and _is_available(other)]
    # The current outfit is only dismissed once there is something to replace it.
    replacement = (
        ready[0]
        if ready
        else _generate(db, user, outfit.day, outfit.occasion, forecast, existing)[0]
    )
    outfit.dismissed_at = dt.datetime.now(dt.UTC)
    db.commit()
    return replacement


def wear(db: Session, outfit: Outfit) -> Outfit:
    if outfit.worn_at is None:
        now = dt.datetime.now(dt.UTC)
        outfit.worn_at = now
        for garment_id in _combo(outfit.garment_ids()):
            garment = db.get(Garment, garment_id)
            if garment is not None:
                garment.last_worn_at = now
        db.commit()
    return outfit
