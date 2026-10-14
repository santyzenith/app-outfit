import json
import uuid
from dataclasses import dataclass

from app.ai import openrouter
from app.ai.outfits import SLOTS, describe_garment
from app.config import get_settings
from app.models import Garment, GarmentCategory

PROMPT = """This photo shows an outfit someone wants to recreate using only clothes they already \
own. Their closet (JSON): {garments}

1. Identify the pieces the look actually has, one per slot: top, bottom, one_piece (dress or \
jumpsuit), outerwear, shoes, accessory (at most one: bag, cap, hat or scarf). Ignore jewelry, \
belts and socks.
2. For each of those pieces, pick by its "ref" the closet garment of the same category that is \
the closest stand-in in type, color and style. Pick it only if it keeps the spirit of the look; \
otherwise leave the slot null and list the piece under "missing" with a short name in neutral \
Latin American Spanish, e.g. "Abrigo largo camel". Leave null every slot the look does not have.
3. "explanation": one short sentence, at most 25 words, in neutral Latin American Spanish, \
addressing the person as "tú", saying how their version captures the look. Mention only \
garments you picked. No emojis, no refs.
If the photo does not show an outfit or clothing, set is_look to false."""

_SLOT_SCHEMA = {"type": ["string", "null"]}
SCHEMA = {
    "type": "object",
    "properties": {
        "is_look": {"type": "boolean"},
        **dict.fromkeys(SLOTS, _SLOT_SCHEMA),
        "missing": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": SLOTS},
                    "name": {"type": "string"},
                },
                "required": ["category", "name"],
                "additionalProperties": False,
            },
        },
        "explanation": {"type": "string"},
    },
    "required": ["is_look", *SLOTS, "missing", "explanation"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class MissingPiece:
    category: GarmentCategory
    name: str


@dataclass(frozen=True)
class LookMatch:
    is_look: bool
    garment_ids: dict[GarmentCategory, uuid.UUID | None]
    missing: list[MissingPiece]
    explanation: str


def extraer_estilo(photo: bytes, closet: list[Garment]) -> LookMatch:
    by_ref = {f"g{index}": garment for index, garment in enumerate(closet, start=1)}
    prompt = PROMPT.format(
        garments=json.dumps(
            [describe_garment(ref, garment) for ref, garment in by_ref.items()],
            ensure_ascii=False,
        )
    )
    data = openrouter.chat_json(get_settings().vision_model, prompt, SCHEMA, image=photo)

    garment_ids: dict[GarmentCategory, uuid.UUID | None] = {}
    for category in GarmentCategory:
        garment = by_ref.get(data.get(category.value) or "")
        # A ref used in the wrong slot is dropped rather than trusted.
        valid = garment is not None and garment.category == category
        garment_ids[category] = garment.id if valid else None
    try:
        missing = [
            MissingPiece(GarmentCategory(item["category"]), str(item["name"])[:80])
            for item in data.get("missing", [])
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise openrouter.AIError(f"invalid look match: {data}") from exc
    return LookMatch(
        is_look=bool(data.get("is_look")),
        garment_ids=garment_ids,
        missing=missing,
        explanation=str(data.get("explanation", "")).strip(),
    )
