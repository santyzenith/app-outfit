import datetime as dt
import uuid

import pytest
from sqlalchemy import select

from app import jobs
from app.models import Job, Occasion, Outfit, User
from app.outfits import pregeneration
from app.outfits.pregeneration import default_occasion, enqueue_due
from tests.conftest import auth_header
from tests.test_outfits import MILD, closet, stylist  # noqa: F401  (shared fixtures)

ECUADOR = -300
# A Wednesday, 10:00 UTC: 05:00 in Ecuador, inside the preparation window.
EARLY_MORNING = dt.datetime(2026, 10, 14, 10, 0, tzinfo=dt.UTC)
LOCAL_DAY = dt.date(2026, 10, 14)


@pytest.fixture
def user(client) -> dict[str, str]:
    return auth_header(client.post("/v1/auth/guest").json())


def open_app(client, headers, tz=ECUADOR, day=dt.date(2026, 10, 13)):
    query = {"day": day.isoformat(), "occasion": "casual", "lat": -2.9, "lon": -79.0, "tz": tz}
    return client.get("/v1/outfits/today", params=query, headers=headers)


def the_user(db) -> User:
    return db.scalar(select(User))


def test_opening_the_app_remembers_where_and_when(client, db, user, closet, stylist):
    open_app(client, user)

    saved = the_user(db)
    assert (saved.latitude, saved.longitude, saved.utc_offset_minutes) == (-2.9, -79.0, ECUADOR)
    assert saved.last_seen_at is not None


def test_an_outfit_is_queued_early_in_the_users_morning(client, db, user, closet, stylist):
    open_app(client, user)
    the_user(db).last_seen_at = EARLY_MORNING - dt.timedelta(hours=10)
    db.commit()

    assert enqueue_due(db, EARLY_MORNING) == 1
    # A second pass while the job is waiting must not queue it again.
    assert enqueue_due(db, EARLY_MORNING) == 0

    job = db.scalar(select(Job).where(Job.kind == pregeneration.PREGENERATE_JOB))
    assert job.payload["day"] == LOCAL_DAY.isoformat()


@pytest.mark.parametrize(
    ("now", "seen_days_ago"),
    [
        (EARLY_MORNING + dt.timedelta(hours=6), 0),
        (EARLY_MORNING, 30),
    ],
    ids=["outside the morning window", "user stopped opening the app"],
)
def test_nothing_is_queued_when_it_is_not_due(
    client, db, user, closet, stylist, now, seen_days_ago
):
    open_app(client, user)
    the_user(db).last_seen_at = now - dt.timedelta(days=seen_days_ago, hours=1)
    db.commit()

    assert enqueue_due(db, now) == 0


def test_the_prepared_outfit_is_the_one_the_app_shows(
    client, db, user, closet, stylist, monkeypatch
):
    monkeypatch.setattr(pregeneration, "get_forecast", lambda lat, lon, day: MILD)
    open_app(client, user)
    the_user(db).last_seen_at = EARLY_MORNING - dt.timedelta(hours=10)
    db.commit()
    enqueue_due(db, EARLY_MORNING)
    calls_before = len(stylist)

    while jobs.run_next_job(db):
        pass

    prepared = db.scalar(select(Outfit).where(Outfit.day == LOCAL_DAY))
    assert prepared.occasion == Occasion.WORK
    shown = client.get(
        "/v1/outfits/today",
        params={"day": LOCAL_DAY.isoformat(), "occasion": "work"},
        headers=user,
    ).json()
    assert shown["id"] == str(prepared.id)
    # Opening the app did not need another model call.
    assert len(stylist) == calls_before + 1
    assert enqueue_due(db, EARLY_MORNING) == 0


def test_preparing_for_an_empty_closet_does_nothing(client, db, user):
    user_id = uuid.UUID(client.get("/v1/me", headers=user).json()["id"])
    jobs.enqueue(
        db, pregeneration.PREGENERATE_JOB, {"user_id": str(user_id), "day": LOCAL_DAY.isoformat()}
    )
    db.commit()

    jobs.run_next_job(db)

    assert db.scalar(select(Outfit)) is None


def test_default_occasion_follows_the_week():
    wednesday_morning = dt.datetime(2026, 10, 14, 7)
    friday_evening = dt.datetime(2026, 10, 16, 19)
    sunday_morning = dt.datetime(2026, 10, 18, 9)

    assert default_occasion(wednesday_morning) == Occasion.WORK
    assert default_occasion(friday_evening) == Occasion.NIGHT_OUT
    assert default_occasion(sunday_morning) == Occasion.CASUAL
