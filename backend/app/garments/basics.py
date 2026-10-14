# ruff: noqa: E501
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.garments import crear_basico
from app.garments.images import normalize_catalog_image
from app.models import Formality, Garment, GarmentCategory, GarmentStatus, User, Warmth
from app.storage import Storage, get_storage

TOP, BOTTOM, ONE_PIECE = GarmentCategory.TOP, GarmentCategory.BOTTOM, GarmentCategory.ONE_PIECE
OUTER, SHOES, ACCESSORY = (
    GarmentCategory.OUTERWEAR,
    GarmentCategory.SHOES,
    GarmentCategory.ACCESSORY,
)
LIGHT, MEDIUM, WARM = Warmth.LIGHT, Warmth.MEDIUM, Warmth.WARM
CASUAL, SMART, FORMAL = Formality.CASUAL, Formality.SMART, Formality.FORMAL


@dataclass(frozen=True)
class Basic:
    key: str
    name: str
    category: GarmentCategory
    color: str
    warmth: Warmth
    formality: Formality
    # English description for the image model.
    description: str


# One basic per line reads as a table; the formatter would split each into nine lines.
# fmt: off
CATALOG = [
    Basic("white_tee", "Camiseta blanca", TOP, "blanco", LIGHT, CASUAL, "a plain white crew-neck short-sleeve cotton t-shirt"),
    Basic("black_tee", "Camiseta negra", TOP, "negro", LIGHT, CASUAL, "a plain black crew-neck short-sleeve cotton t-shirt"),
    Basic("grey_tee", "Camiseta gris", TOP, "gris", LIGHT, CASUAL, "a plain heather grey crew-neck short-sleeve cotton t-shirt"),
    Basic("white_shirt", "Camisa blanca", TOP, "blanco", LIGHT, SMART, "a plain white long-sleeve button-down cotton shirt"),
    Basic("light_blue_shirt", "Camisa celeste", TOP, "celeste", LIGHT, SMART, "a plain light blue long-sleeve button-down cotton shirt"),
    Basic("navy_polo", "Polo azul marino", TOP, "azul marino", LIGHT, CASUAL, "a plain navy blue short-sleeve pique polo shirt"),
    Basic("blue_jeans", "Jean azul", BOTTOM, "azul", MEDIUM, CASUAL, "classic mid-blue straight-leg denim jeans"),
    Basic("black_jeans", "Jean negro", BOTTOM, "negro", MEDIUM, CASUAL, "plain black straight-leg denim jeans"),
    Basic("beige_chinos", "Pantalón beige", BOTTOM, "beige", MEDIUM, SMART, "plain beige cotton chino trousers"),
    Basic("black_trousers", "Pantalón de vestir negro", BOTTOM, "negro", MEDIUM, FORMAL, "plain black tailored dress trousers"),
    Basic("denim_shorts", "Short de jean", BOTTOM, "azul", LIGHT, CASUAL, "plain mid-blue denim shorts"),
    Basic("black_skirt", "Falda negra", BOTTOM, "negro", LIGHT, SMART, "a plain black knee-length A-line skirt"),
    Basic("black_leggings", "Leggings negros", BOTTOM, "negro", MEDIUM, CASUAL, "plain black full-length leggings"),
    Basic("black_dress", "Vestido negro", ONE_PIECE, "negro", LIGHT, SMART, "a plain black knee-length short-sleeve dress"),
    Basic("grey_sweater", "Suéter gris", OUTER, "gris", MEDIUM, CASUAL, "a plain grey crew-neck knit sweater"),
    Basic("grey_hoodie", "Sudadera con capucha", OUTER, "gris", MEDIUM, CASUAL, "a plain heather grey pullover hoodie"),
    Basic("denim_jacket", "Chaqueta de jean", OUTER, "azul", MEDIUM, CASUAL, "a plain mid-blue denim jacket"),
    Basic("rain_jacket", "Chaqueta impermeable", OUTER, "negro", MEDIUM, CASUAL, "a plain black hooded rain jacket"),
    Basic("black_blazer", "Blazer negro", OUTER, "negro", MEDIUM, FORMAL, "a plain black single-breasted blazer"),
    Basic("camel_coat", "Abrigo camel", OUTER, "camel", WARM, SMART, "a plain camel wool long coat"),
    Basic("white_sneakers", "Zapatillas blancas", SHOES, "blanco", LIGHT, CASUAL, "a pair of plain white leather low-top sneakers"),
    Basic("black_dress_shoes", "Zapatos de vestir negros", SHOES, "negro", MEDIUM, FORMAL, "a pair of plain black leather lace-up dress shoes"),
    Basic("black_boots", "Botines negros", SHOES, "negro", WARM, SMART, "a pair of plain black leather ankle boots"),
    Basic("black_sandals", "Sandalias negras", SHOES, "negro", LIGHT, CASUAL, "a pair of plain black strappy flat sandals"),
    Basic("black_cap", "Gorra negra", ACCESSORY, "negro", LIGHT, CASUAL, "a plain black baseball cap"),
    Basic("grey_scarf", "Bufanda gris", ACCESSORY, "gris", WARM, CASUAL, "a plain grey knit scarf"),
    Basic("black_bag", "Bolso negro", ACCESSORY, "negro", MEDIUM, SMART, "a plain black leather shoulder bag"),
]
# fmt: on
BY_KEY = {basic.key: basic for basic in CATALOG}


class UnknownBasicError(Exception):
    pass


def image_path(basic: Basic) -> str:
    return f"_basics/{basic.key}.jpg"


def available(storage: Storage) -> list[Basic]:
    # Only basics whose image was already generated can be offered.
    return [basic for basic in CATALOG if storage.exists(image_path(basic))]


def owned_keys(db: Session, user: User) -> set[str]:
    query = select(Garment.basic_key).where(
        Garment.user_id == user.id, Garment.basic_key.is_not(None)
    )
    return set(db.scalars(query))


def add_to_closet(db: Session, storage: Storage, user: User, keys: list[str]) -> list[Garment]:
    offered = {basic.key for basic in available(storage)}
    if any(key not in offered for key in keys):
        raise UnknownBasicError
    garments = []
    for key in dict.fromkeys(keys):
        basic = BY_KEY[key]
        garment_id = uuid.uuid4()
        # The user gets a copy, so deleting the garment never touches the shared image.
        path = storage.save(user.id, f"{garment_id}_catalog.jpg", storage.read(image_path(basic)))
        garment = Garment(
            id=garment_id,
            user_id=user.id,
            status=GarmentStatus.READY,
            basic_key=basic.key,
            category=basic.category,
            name=basic.name,
            color=basic.color,
            warmth=basic.warmth,
            formality=basic.formality,
            original_path=path,
            image_path=path,
        )
        db.add(garment)
        garments.append(garment)
    db.commit()
    return garments


def generate_missing(storage: Storage) -> None:
    for basic in CATALOG:
        if storage.exists(image_path(basic)):
            continue
        print(f"generating {basic.key}")
        storage.save_shared(
            image_path(basic), normalize_catalog_image(crear_basico(basic.description))
        )


if __name__ == "__main__":
    # Paid: one image model call per missing basic (about $0.02 each).
    generate_missing(get_storage())
