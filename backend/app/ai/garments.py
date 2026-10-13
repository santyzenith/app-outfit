from dataclasses import dataclass

from app.ai import openrouter
from app.config import get_settings
from app.models import Formality, GarmentCategory, Warmth

ANALYZE_PROMPT = (
    "You catalog clothes for a virtual closet app. Look at the photo and list every distinct "
    "clothing item, pair of shoes or wearable accessory its owner wants to catalog. Usually "
    "there is exactly one. When there are several, list only the ones that are almost completely "
    "visible, whether laid out or worn by a person; skip anything mostly hidden, piled up or in "
    "the background. A pair of shoes is one item. If the photo shows no such item, return an "
    "empty list. For each item:\n"
    "- category: top (t-shirts, shirts, blouses, thin sweaters worn as the main upper piece), "
    "bottom (pants, jeans, shorts, skirts), one_piece (dresses, jumpsuits), outerwear (jackets, "
    "coats, hoodies, cardigans worn over a top), shoes, accessory (bags, caps, hats, scarves).\n"
    "- name: a short label in neutral Latin American Spanish, 2 to 5 words, lowercase except the "
    "first letter, e.g. 'Camiseta gris con logo'. Use words that are natural in Ecuador and "
    "understood everywhere: 'jean' (never 'mezclilla' or 'vaqueros'), 'camiseta' (never 'playera' "
    "or 'remera'), 'chaqueta' (never 'chamarra' or 'campera'), 'suéter', 'zapatos deportivos' "
    "(never 'tenis' or 'zapatillas'). Do not include brand names.\n"
    "- color: the dominant color in Spanish, one or two words, e.g. 'azul marino'.\n"
    "- warmth: light (hot weather), medium, or warm (cold weather).\n"
    "- formality: casual, smart (smart casual, office) or formal.\n"
    "- description: a short English phrase that tells this item apart from the others in the "
    "photo by its look and position, e.g. 'the grey t-shirt with a logo, on the left'."
)

ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": [c.value for c in GarmentCategory]},
        "name": {"type": "string"},
        "color": {"type": "string"},
        "warmth": {"type": "string", "enum": [w.value for w in Warmth]},
        "formality": {"type": "string", "enum": [f.value for f in Formality]},
        "description": {"type": "string"},
    },
    "required": ["category", "name", "color", "warmth", "formality", "description"],
    "additionalProperties": False,
}

ANALYZE_SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": ITEM_SCHEMA}},
    "required": ["items"],
    "additionalProperties": False,
}

RECREATE_PROMPT = (
    "This is a casual photo of a clothing item taken by its owner. Recreate exactly this same "
    "item as a clean e-commerce catalog photo: the item alone, front view, neatly laid flat and "
    "unwrinkled, evenly lit, centered, on a plain pure white background. No hanger, no person, "
    "no furniture, no props. Preserve exactly the original colors, fabric texture, pattern, "
    "logos, prints, text, buttons, zippers, stitching and proportions. Do not add, remove or "
    "redesign anything. If the item is folded, rolled or partly hidden, show it fully unfolded "
    "with its complete natural shape, continuing the same fabric and color over the hidden parts "
    "without inventing new details. If the item is footwear, show the pair side by side."
)

ONE_OF_MANY_PROMPT = (
    "This photo shows several clothing items. Recreate ONLY this one: {item}. Show exactly that "
    "same item as a clean e-commerce catalog photo: the item alone, front view, neatly laid flat "
    "and unwrinkled, evenly lit, centered, on a plain pure white background. No other items, no "
    "hanger, no person, no furniture, no props. Preserve exactly its original colors, fabric "
    "texture, pattern, logos, prints, text, buttons, zippers, stitching and proportions. Do not "
    "add, remove or redesign anything. If the item is footwear, show the pair side by side."
)


@dataclass(frozen=True)
class GarmentAnalysis:
    category: GarmentCategory
    name: str
    color: str
    warmth: Warmth
    formality: Formality
    # Tells this item apart when the photo shows several.
    description: str


def analizar_prenda(photo: bytes) -> list[GarmentAnalysis]:
    data = openrouter.chat_json(
        get_settings().vision_model, ANALYZE_PROMPT, ANALYZE_SCHEMA, image=photo
    )
    try:
        return [
            GarmentAnalysis(
                category=GarmentCategory(item["category"]),
                name=str(item["name"])[:120],
                color=str(item["color"])[:60],
                warmth=Warmth(item["warmth"]),
                formality=Formality(item["formality"]),
                description=str(item["description"])[:200],
            )
            for item in data["items"]
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise openrouter.AIError(f"invalid garment analysis: {data}") from exc


def recrear_prenda(photo: bytes, focus: str | None = None) -> bytes:
    prompt = ONE_OF_MANY_PROMPT.format(item=focus) if focus else RECREATE_PROMPT
    return openrouter.generate_image(get_settings().image_model, prompt, photo)
