import io
from datetime import UTC, datetime, timedelta

import pytest
from PIL import Image
from sqlalchemy import select, update

from app import jobs
from app.ai.garments import GarmentAnalysis
from app.ai.openrouter import AIError
from app.config import get_settings
from app.garments import processing
from app.garments.images import normalize_catalog_image
from app.models import Formality, GarmentCategory, Job, JobStatus, Warmth
from app.storage import get_storage
from tests.conftest import auth_header


def image_bytes(size=(800, 600), color="navy", fmt="JPEG") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, fmt)
    return buffer.getvalue()


ANALYSIS = GarmentAnalysis(
    category=GarmentCategory.TOP,
    name="Camiseta azul",
    color="azul marino",
    warmth=Warmth.LIGHT,
    formality=Formality.CASUAL,
    description="the navy t-shirt",
)
JEAN = GarmentAnalysis(
    category=GarmentCategory.BOTTOM,
    name="Jean negro",
    color="negro",
    warmth=Warmth.MEDIUM,
    formality=Formality.CASUAL,
    description="the black jeans on the right",
)


def failing_model(photo: bytes, focus: str | None = None) -> bytes:
    raise AIError("model is down")


def working_model(photo: bytes, focus: str | None = None) -> bytes:
    return image_bytes(fmt="PNG")


@pytest.fixture
def fake_ai(monkeypatch):
    # Replaces the two paid model calls and counts how often each one runs.
    calls = {"analyze": 0, "recreate": 0}

    def analyze(photo: bytes) -> list[GarmentAnalysis]:
        calls["analyze"] += 1
        return [ANALYSIS]

    def recreate(photo: bytes, focus: str | None = None) -> bytes:
        calls["recreate"] += 1
        return image_bytes(size=(2048, 2048), color="white", fmt="PNG")

    monkeypatch.setattr(processing, "analizar_prenda", analyze)
    monkeypatch.setattr(processing, "recrear_prenda", recreate)
    monkeypatch.setattr(jobs, "RETRY_DELAY", timedelta(0))
    return calls


@pytest.fixture
def user(client) -> dict[str, str]:
    return auth_header(client.post("/v1/auth/guest").json())


def upload(client, headers, data: bytes | None = None):
    files = {"photo": ("photo.jpg", data or image_bytes(), "image/jpeg")}
    return client.post("/v1/garments", files=files, headers=headers)


def run_all_jobs(db) -> None:
    while jobs.run_next_job(db):
        pass


def test_upload_stores_the_photo_and_queues_processing(client, db, user):
    response = upload(client, user)

    assert response.status_code == 202
    assert response.json()["status"] == "processing"
    url = f"/v1/garments/{response.json()['id']}/image?variant=original"
    original = client.get(url, headers=user)
    assert original.status_code == 200
    assert original.headers["content-type"] == "image/jpeg"
    job = db.scalar(select(Job))
    assert job.status == JobStatus.QUEUED
    assert job.payload == {"garment_id": response.json()["id"]}


def test_upload_shrinks_large_photos(client, user):
    garment = upload(client, user, image_bytes(size=(4000, 3000))).json()

    original = client.get(f"/v1/garments/{garment['id']}/image?variant=original", headers=user)

    assert max(Image.open(io.BytesIO(original.content)).size) == 1600


def test_upload_rejects_what_is_not_an_image(client, user):
    response = upload(client, user, b"definitely not an image")

    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_image"


def test_upload_requires_a_session(client):
    assert upload(client, {}).status_code == 401


def test_processing_catalogs_the_garment(client, db, user, fake_ai):
    garment = upload(client, user).json()

    assert jobs.run_next_job(db) is True

    ready = client.get(f"/v1/garments/{garment['id']}", headers=user).json()
    assert ready["status"] == "ready"
    assert ready["category"] == "top"
    assert ready["name"] == "Camiseta azul"
    assert ready["warmth"] == "light"
    assert ready["image_version"]
    catalog = client.get(f"/v1/garments/{garment['id']}/image", headers=user)
    assert catalog.status_code == 200
    assert Image.open(io.BytesIO(catalog.content)).size == (1024, 1024)
    assert jobs.run_next_job(db) is False


def test_catalog_image_is_missing_until_processing_finishes(client, user):
    garment = upload(client, user).json()

    response = client.get(f"/v1/garments/{garment['id']}/image", headers=user)

    assert response.status_code == 404
    assert response.json()["detail"] == "image_not_ready"


def test_photo_without_a_garment_fails_without_generating_an_image(
    client, db, user, fake_ai, monkeypatch
):
    monkeypatch.setattr(processing, "analizar_prenda", lambda photo: [])
    garment = upload(client, user).json()

    jobs.run_next_job(db)

    failed = client.get(f"/v1/garments/{garment['id']}", headers=user).json()
    assert failed["status"] == "failed"
    assert failed["failure_reason"] == "not_a_garment"
    assert fake_ai["recreate"] == 0


def test_a_photo_with_several_items_becomes_several_garments(
    client, db, user, fake_ai, monkeypatch
):
    asked_for = []

    def recreate(photo: bytes, focus: str | None = None) -> bytes:
        asked_for.append(focus)
        return image_bytes(fmt="PNG")

    monkeypatch.setattr(processing, "analizar_prenda", lambda photo: [ANALYSIS, JEAN])
    monkeypatch.setattr(processing, "recrear_prenda", recreate)
    upload(client, user)

    jobs.run_next_job(db)
    listed = client.get("/v1/garments", headers=user).json()
    assert {g["name"]: g["status"] for g in listed} == {
        "Camiseta azul": "ready",
        "Jean negro": "processing",
    }

    run_all_jobs(db)

    garments = client.get("/v1/garments", headers=user).json()
    assert {g["status"] for g in garments} == {"ready"}
    assert asked_for == [ANALYSIS.description, JEAN.description]
    for garment in garments:
        url = f"/v1/garments/{garment['id']}/image?variant=original"
        assert client.get(url, headers=user).status_code == 200


def test_a_photo_cannot_become_more_garments_than_the_limit(client, db, user, fake_ai, monkeypatch):
    many = [ANALYSIS] * (processing.MAX_ITEMS_PER_PHOTO + 3)
    monkeypatch.setattr(processing, "analizar_prenda", lambda photo: many)
    upload(client, user)

    run_all_jobs(db)

    garments = client.get("/v1/garments", headers=user).json()
    assert len(garments) == processing.MAX_ITEMS_PER_PHOTO
    assert fake_ai["recreate"] == processing.MAX_ITEMS_PER_PHOTO


def test_retrying_a_garment_from_a_shared_photo_does_not_split_it_again(
    client, db, user, fake_ai, monkeypatch
):
    monkeypatch.setattr(processing, "analizar_prenda", lambda photo: [ANALYSIS, JEAN])
    upload(client, user)
    jobs.run_next_job(db)
    monkeypatch.setattr(processing, "recrear_prenda", failing_model)
    run_all_jobs(db)
    failed = next(
        g for g in client.get("/v1/garments", headers=user).json() if g["status"] == "failed"
    )
    monkeypatch.setattr(processing, "recrear_prenda", working_model)

    client.post(f"/v1/garments/{failed['id']}/retry", headers=user)
    run_all_jobs(db)

    garments = client.get("/v1/garments", headers=user).json()
    assert sorted(g["name"] for g in garments) == ["Camiseta azul", "Jean negro"]
    assert {g["status"] for g in garments} == {"ready"}


def test_processing_retries_and_then_gives_up(client, db, user, fake_ai, monkeypatch):
    def broken(photo: bytes, focus: str | None = None) -> bytes:
        fake_ai["recreate"] += 1
        raise AIError("model is down")

    monkeypatch.setattr(processing, "recrear_prenda", broken)
    garment = upload(client, user).json()

    run_all_jobs(db)

    failed = client.get(f"/v1/garments/{garment['id']}", headers=user).json()
    assert failed["status"] == "failed"
    assert failed["failure_reason"] == "processing_error"
    assert fake_ai["recreate"] == jobs.MAX_ATTEMPTS
    assert db.scalar(select(Job)).status == JobStatus.FAILED


def test_a_failed_garment_can_be_retried(client, db, user, fake_ai, monkeypatch):
    monkeypatch.setattr(processing, "recrear_prenda", failing_model)
    garment = upload(client, user).json()
    run_all_jobs(db)
    monkeypatch.setattr(processing, "recrear_prenda", working_model)

    retried = client.post(f"/v1/garments/{garment['id']}/retry", headers=user)
    run_all_jobs(db)

    assert retried.status_code == 202
    assert client.get(f"/v1/garments/{garment['id']}", headers=user).json()["status"] == "ready"


def test_only_failed_garments_can_be_retried(client, user):
    garment = upload(client, user).json()

    response = client.post(f"/v1/garments/{garment['id']}/retry", headers=user)

    assert response.status_code == 409


def test_garments_are_private_to_their_owner(client, user):
    garment = upload(client, user).json()
    stranger = auth_header(client.post("/v1/auth/guest").json())
    url = f"/v1/garments/{garment['id']}"

    assert client.get(url, headers=stranger).status_code == 404
    assert client.get(f"{url}/image?variant=original", headers=stranger).status_code == 404
    assert client.patch(url, json={"name": "Otra"}, headers=stranger).status_code == 404
    assert client.delete(url, headers=stranger).status_code == 404
    assert client.get("/v1/garments", headers=stranger).json() == []


def test_list_filters_by_status(client, db, user, fake_ai):
    first = upload(client, user).json()
    jobs.run_next_job(db)
    second = upload(client, user).json()

    everything = client.get("/v1/garments", headers=user).json()
    ready = client.get("/v1/garments?status=ready", headers=user).json()

    assert {g["id"] for g in everything} == {first["id"], second["id"]}
    assert [g["id"] for g in ready] == [first["id"]]


def test_the_user_can_correct_the_catalog(client, db, user, fake_ai):
    garment = upload(client, user).json()
    jobs.run_next_job(db)
    url = f"/v1/garments/{garment['id']}"

    updated = client.patch(url, json={"category": "outerwear", "warmth": "warm"}, headers=user)

    assert updated.json()["category"] == "outerwear"
    assert updated.json()["warmth"] == "warm"
    assert updated.json()["name"] == "Camiseta azul"
    assert client.patch(url, json={"warmth": "lava"}, headers=user).status_code == 422


def test_deleting_a_garment_removes_its_files(client, db, user, fake_ai):
    garment = upload(client, user).json()
    jobs.run_next_job(db)
    user_folder = get_storage().path(client.get("/v1/me", headers=user).json()["id"])
    assert len(list(user_folder.iterdir())) == 2

    assert client.delete(f"/v1/garments/{garment['id']}", headers=user).status_code == 204

    assert list(user_folder.iterdir()) == []
    assert client.get(f"/v1/garments/{garment['id']}", headers=user).status_code == 404


def test_deleting_the_account_removes_the_photos(client, user):
    upload(client, user)
    user_folder = get_storage().path(client.get("/v1/me", headers=user).json()["id"])
    assert user_folder.exists()

    client.delete("/v1/me", headers=user)

    assert not user_folder.exists()


def test_jobs_abandoned_by_a_dead_worker_are_queued_again(client, db, user):
    upload(client, user)
    long_ago = datetime.now(UTC) - jobs.STALE_AFTER - timedelta(seconds=1)
    db.execute(update(Job).values(status=JobStatus.RUNNING, locked_at=long_ago))

    assert jobs.requeue_stale_jobs(db) == 1
    assert db.scalar(select(Job)).status == JobStatus.QUEUED


def test_storage_refuses_paths_outside_its_root():
    with pytest.raises(ValueError):
        get_storage().path("../outside.txt")


def png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def test_catalog_images_get_a_pure_white_background():
    almost_white = Image.new("RGB", (400, 400), (250, 251, 252))
    almost_white.paste((30, 40, 90), (150, 150, 250, 250))

    result = Image.open(io.BytesIO(normalize_catalog_image(png_bytes(almost_white))))

    assert min(result.getpixel((3, 3))) >= 254
    assert max(result.getpixel((200, 200))) < 100


def test_catalog_images_that_fill_the_frame_keep_their_colors():
    dark = Image.new("RGB", (400, 400), (60, 60, 60))

    result = Image.open(io.BytesIO(normalize_catalog_image(png_bytes(dark))))

    assert max(result.getpixel((200, 200))) < 70


def test_regenerating_replaces_the_catalog_image_file(client, db, user, fake_ai, monkeypatch):
    monkeypatch.setattr(processing, "recrear_prenda", failing_model)
    garment = upload(client, user).json()
    run_all_jobs(db)
    monkeypatch.setattr(processing, "recrear_prenda", working_model)
    client.post(f"/v1/garments/{garment['id']}/retry", headers=user)
    run_all_jobs(db)

    user_folder = get_storage().path(client.get("/v1/me", headers=user).json()["id"])
    catalog_files = [path for path in user_folder.iterdir() if "_catalog_" in path.name]

    assert len(catalog_files) == 1


def test_uploads_stop_at_the_daily_limit(client, user, monkeypatch):
    monkeypatch.setattr(get_settings(), "garments_per_day", 1)
    assert upload(client, user).status_code == 202

    response = upload(client, user)

    assert response.status_code == 429
    assert response.json()["detail"] == "upload_limit_reached"


def test_a_guest_closet_moves_to_the_account_they_sign_in_to(
    client, db, user, fake_ai, make_id_token
):
    account = client.post("/v1/auth/google", json={"id_token": make_id_token()}).json()
    garment = upload(client, user).json()
    jobs.run_next_job(db)
    guest_id = client.get("/v1/me", headers=user).json()["id"]

    client.post("/v1/auth/google", json={"id_token": make_id_token()}, headers=user)

    owner = auth_header(account)
    assert [g["id"] for g in client.get("/v1/garments", headers=owner).json()] == [garment["id"]]
    url = f"/v1/garments/{garment['id']}/image"
    assert client.get(url, headers=owner).status_code == 200
    assert client.get(f"{url}?variant=original", headers=owner).status_code == 200
    assert not get_storage().path(guest_id).exists()
    assert client.get("/v1/me", headers=user).status_code == 401


def test_thumbnails_are_small_and_go_away_with_the_garment(client, db, user, fake_ai):
    garment = upload(client, user).json()
    jobs.run_next_job(db)
    url = f"/v1/garments/{garment['id']}/image?size=thumb"

    first = client.get(url, headers=user)
    again = client.get(url, headers=user)
    original = client.get(f"{url}&variant=original", headers=user)

    assert first.status_code == again.status_code == original.status_code == 200
    assert max(Image.open(io.BytesIO(first.content)).size) == 384
    user_folder = get_storage().path(client.get("/v1/me", headers=user).json()["id"])
    assert len(list(user_folder.glob("*_thumb.jpg"))) == 2
    client.delete(f"/v1/garments/{garment['id']}", headers=user)
    assert list(user_folder.iterdir()) == []


def test_optional_details_can_be_set_and_cleared(client, db, user, fake_ai):
    garment = upload(client, user).json()
    jobs.run_next_job(db)
    url = f"/v1/garments/{garment['id']}"

    filled = client.patch(
        url, json={"brand": " Zara ", "size": "M", "notes": "Lavar a mano"}, headers=user
    )
    cleared = client.patch(url, json={"brand": ""}, headers=user)

    assert filled.json()["brand"] == "Zara"
    assert filled.json()["notes"] == "Lavar a mano"
    assert cleared.json()["brand"] is None
    assert cleared.json()["size"] == "M"
