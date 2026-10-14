import io

import pytest
from PIL import Image

from app.garments import basics
from app.storage import get_storage
from tests.conftest import auth_header
from tests.test_garments import image_bytes


@pytest.fixture
def user(client) -> dict[str, str]:
    return auth_header(client.post("/v1/auth/guest").json())


def add(client, headers, *keys: str):
    return client.post("/v1/basics", json={"keys": list(keys)}, headers=headers)


def test_lists_every_shape_with_its_colors_and_what_is_owned(client, user):
    listed = client.get("/v1/basics", headers=user).json()
    assert [shape["key"] for shape in listed] == [shape.key for shape in basics.SHAPES]
    assert not any(color["owned"] for shape in listed for color in shape["colors"])

    add(client, user, "tee:black")

    tee = next(
        shape for shape in client.get("/v1/basics", headers=user).json() if shape["key"] == "tee"
    )
    assert [color["key"] for color in tee["colors"] if color["owned"]] == ["black"]
    assert next(color for color in tee["colors"] if color["key"] == "white")["name"] == "blanca"


def test_adding_basics_names_them_in_agreement_with_the_shape(client, user):
    response = add(client, user, "tee:white", "jeans:black", "sneakers:white", "tee:white")

    assert response.status_code == 201
    garments = response.json()
    assert [g["name"] for g in garments] == ["Camiseta blanca", "Jean negro", "Zapatillas blancas"]
    tee = garments[0]
    assert tee["status"] == "ready"
    assert tee["basic_key"] == "tee:white"
    assert tee["category"] == "top"
    assert tee["color"] == "blanco"
    assert client.get(f"/v1/garments/{tee['id']}/image", headers=user).status_code == 200


@pytest.mark.parametrize("bad_key", ["jeans:pink", "crown:white", "tee"])
def test_unknown_basics_add_nothing(client, user, bad_key):
    response = add(client, user, "tee:white", bad_key)

    assert response.status_code == 422
    assert client.get("/v1/garments", headers=user).json() == []


def test_basic_images_are_painted_and_served_full_and_as_thumbnails(client, user):
    full = client.get("/v1/basics/tee/image?color=navy", headers=user)
    thumb = client.get("/v1/basics/tee/image?color=navy&size=thumb", headers=user)

    assert full.status_code == thumb.status_code == 200
    assert len(thumb.content) < len(full.content)
    assert client.get("/v1/basics/tee/image?color=camel", headers=user).status_code == 404


def test_recoloring_keeps_the_background_white_and_paints_the_garment():
    tee = basics.SHAPES_BY_KEY["tee"]
    painted = basics.recolor(
        basics.base_path(tee).read_bytes(), basics.COLORS["red"], basics.garment_mask(tee)
    )

    image = Image.open(io.BytesIO(painted)).convert("RGB")
    width, height = image.size
    assert image.getpixel((2, 2)) == (255, 255, 255)
    red, green, blue = image.getpixel((width // 2, height // 2))
    assert red > green + 60 and red > blue + 60


def test_deleting_a_basic_garment_keeps_the_shared_image(client, user):
    garment = add(client, user, "bag:black").json()[0]

    client.delete(f"/v1/garments/{garment['id']}", headers=user)

    assert get_storage().exists("_basics/bag_black.jpg")
    assert client.get("/v1/basics/bag/image?color=black", headers=user).status_code == 200


def test_basic_garments_move_with_a_guest_signing_in(client, make_id_token):
    client.post("/v1/auth/google", json={"id_token": make_id_token()})
    guest = auth_header(client.post("/v1/auth/guest").json())
    add(client, guest, "coat:camel")

    account = client.post(
        "/v1/auth/google", json={"id_token": make_id_token()}, headers=guest
    ).json()

    headers = auth_header(account)
    garment = client.get("/v1/garments", headers=headers).json()[0]
    assert garment["name"] == "Abrigo camel"
    assert client.get(f"/v1/garments/{garment['id']}/image", headers=headers).status_code == 200


def test_generating_only_creates_missing_shapes(monkeypatch, tmp_path):
    # The paid model is replaced, and a one-shape catalog keeps the mask work short.
    calls: list[str] = []

    def create(description: str) -> bytes:
        calls.append(description)
        return image_bytes(size=(512, 512), color="lightgrey", fmt="PNG")

    monkeypatch.setattr(basics, "crear_basico", create)
    monkeypatch.setattr(basics, "BASE_DIR", tmp_path)
    monkeypatch.setattr(basics, "SHAPES", [basics.SHAPES_BY_KEY["tee"]])

    basics.generate_missing()
    basics.generate_missing()

    assert len(calls) == 1
    assert "light grey" in calls[0]
    assert (tmp_path / "tee.jpg").is_file() and (tmp_path / "tee_mask.png").is_file()
