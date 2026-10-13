from dataclasses import dataclass

from app.ai import openrouter
from app.config import get_settings
from app.models import Formality, GarmentCategory, Warmth

ANALYZE_PROMPT = (
    "You catalog clothes for a virtual closet app. Look at the photo and describe the main "
    "clothing item in it. If the photo does not show a clothing item, footwear or a wearable "
    "accessory, set is_garment to false and fill the other fields with your best guess.\n"
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
    "- formality: casual, smart (smart casual, office) or formal."
)

ANALYZE_SCHEMA = {
    "type": "object",
    "properties": {
        "is_garment": {"type": "boolean"},
        "category": {"type": "string", "enum": [c.value for c in GarmentCategory]},
        "name": {"type": "string"},
        "color": {"type": "string"},
        "warmth": {"type": "string", "enum": [w.value for w in Warmth]},
        "formality": {"type": "string", "enum": [f.value for f in Formality]},
    },
    "required": ["is_garment", "category", "name", "color", "warmth", "formality"],
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


@dataclass(frozen=True)
class GarmentAnalysis:
    is_garment: bool
    category: GarmentCategory
    name: str
    color: str
    warmth: Warmth
    formality: Formality


def analizar_prenda(photo: bytes) -> GarmentAnalysis:
    data = openrouter.chat_json(
        get_settings().vision_model, ANALYZE_PROMPT, ANALYZE_SCHEMA, image=photo
    )
    try:
        return GarmentAnalysis(
            is_garment=bool(data["is_garment"]),
            category=GarmentCategory(data["category"]),
            name=str(data["name"])[:120],
            color=str(data["color"])[:60],
            warmth=Warmth(data["warmth"]),
            formality=Formality(data["formality"]),
        )
    except (KeyError, ValueError) as exc:
        raise openrouter.AIError(f"invalid garment analysis: {data}") from exc


def recrear_prenda(photo: bytes) -> bytes:
    return openrouter.generate_image(get_settings().image_model, RECREATE_PROMPT, photo)
