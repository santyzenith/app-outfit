import io
from datetime import UTC, datetime, timedelta

import pytest
from PIL import Image
from sqlalchemy import select, update

from app import jobs
from app.ai.garments import GarmentAnalysis
from app.ai.openrouter import AIError
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
    is_garment=True,
    category=GarmentCategory.TOP,
    name="Camiseta azul",
    color="azul marino",
    warmth=Warmth.LIGHT,
    formality=Formality.CASUAL,
)


def failing_model(photo: bytes) -> bytes:
    raise AIError("model is down")


@pytest.fixture
def fake_ai(monkeypatch):
    # Replaces the two paid model calls and counts how often each one runs.
    calls = {"analyze": 0, "recreate": 0}

    def analyze(photo: bytes) -> GarmentAnalysis:
        calls["analyze"] += 1
        return ANALYSIS

    def recreate(photo: bytes) -> bytes:
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
    not_a_garment = GarmentAnalysis(**{**ANALYSIS.__dict__, "is_garment": False})
    monkeypatch.setattr(processing, "analizar_prenda", lambda photo: not_a_garment)
    garment = upload(client, user).json()

    jobs.run_next_job(db)

    failed = client.get(f"/v1/garments/{garment['id']}", headers=user).json()
    assert failed["status"] == "failed"
    assert failed["failure_reason"] == "not_a_garment"
    assert fake_ai["recreate"] == 0


def test_processing_retries_and_then_gives_up(client, db, user, fake_ai, monkeypatch):
    def broken(photo: bytes) -> bytes:
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
    monkeypatch.setattr(processing, "recrear_prenda", lambda photo: image_bytes(fmt="PNG"))

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
    monkeypatch.setattr(processing, "recrear_prenda", lambda photo: image_bytes(fmt="PNG"))
    client.post(f"/v1/garments/{garment['id']}/retry", headers=user)
    run_all_jobs(db)

    user_folder = get_storage().path(client.get("/v1/me", headers=user).json()["id"])
    catalog_files = [path for path in user_folder.iterdir() if "_catalog_" in path.name]

    assert len(catalog_files) == 1
