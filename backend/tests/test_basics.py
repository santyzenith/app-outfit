import pytest

from app.garments import basics
from app.storage import get_storage
from tests.conftest import auth_header
from tests.test_garments import image_bytes


@pytest.fixture(autouse=True)
def basic_images(monkeypatch) -> list[str]:
    # Replaces the paid image model; every basic gets an image once per test run.
    calls: list[str] = []

    def create(description: str) -> bytes:
        calls.append(description)
        return image_bytes(size=(1024, 1024), color="white", fmt="PNG")

    monkeypatch.setattr(basics, "crear_basico", create)
    basics.generate_missing(get_storage())
    return calls


@pytest.fixture
def user(client) -> dict[str, str]:
    return auth_header(client.post("/v1/auth/guest").json())


def test_generating_skips_basics_that_already_have_an_image(basic_images):
    basic_images.clear()
    basics.generate_missing(get_storage())
    assert basic_images == []


def test_lists_basics_and_marks_the_ones_already_added(client, user):
    listed = client.get("/v1/basics", headers=user).json()
    assert len(listed) == len(basics.CATALOG)
    assert not any(basic["owned"] for basic in listed)

    client.post("/v1/basics", json={"keys": ["white_tee"]}, headers=user)

    owned = {
        basic["key"] for basic in client.get("/v1/basics", headers=user).json() if basic["owned"]
    }
    assert owned == {"white_tee"}


def test_adding_basics_creates_ready_garments_once_per_key(client, user):
    response = client.post(
        "/v1/basics", json={"keys": ["blue_jeans", "white_sneakers", "blue_jeans"]}, headers=user
    )

    assert response.status_code == 201
    garments = response.json()
    assert [g["basic_key"] for g in garments] == ["blue_jeans", "white_sneakers"]
    jeans = garments[0]
    assert jeans["status"] == "ready"
    assert jeans["name"] == "Jean azul"
    assert jeans["category"] == "bottom"
    assert jeans["warmth"] == "medium"
    image = client.get(f"/v1/garments/{jeans['id']}/image", headers=user)
    assert image.status_code == 200


def test_unknown_basic_adds_nothing(client, user):
    response = client.post("/v1/basics", json={"keys": ["white_tee", "gold_crown"]}, headers=user)

    assert response.status_code == 422
    assert client.get("/v1/garments", headers=user).json() == []


def test_deleting_a_basic_garment_keeps_the_shared_image(client, user):
    garment = client.post("/v1/basics", json={"keys": ["black_cap"]}, headers=user).json()[0]

    client.delete(f"/v1/garments/{garment['id']}", headers=user)

    assert get_storage().exists(basics.image_path(basics.BY_KEY["black_cap"]))
    assert client.get("/v1/basics/black_cap/image", headers=user).status_code == 200


def test_basic_images_are_served_full_and_as_thumbnails(client, user):
    full = client.get("/v1/basics/grey_scarf/image", headers=user)
    thumb = client.get("/v1/basics/grey_scarf/image?size=thumb", headers=user)

    assert full.status_code == thumb.status_code == 200
    assert len(thumb.content) < len(full.content)
    assert client.get("/v1/basics/nope/image", headers=user).status_code == 404


def test_basic_garments_move_with_a_guest_signing_in(client, make_id_token):
    client.post("/v1/auth/google", json={"id_token": make_id_token()})
    guest = auth_header(client.post("/v1/auth/guest").json())
    client.post("/v1/basics", json={"keys": ["black_bag"]}, headers=guest)

    account = client.post(
        "/v1/auth/google", json={"id_token": make_id_token()}, headers=guest
    ).json()

    headers = auth_header(account)
    garment = client.get("/v1/garments", headers=headers).json()[0]
    assert garment["basic_key"] == "black_bag"
    assert client.get(f"/v1/garments/{garment['id']}/image", headers=headers).status_code == 200
