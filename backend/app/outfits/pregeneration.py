import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import jobs
from app.models import Job, JobStatus, Occasion, Outfit, User
from app.outfits import service
from app.outfits.weather import get_forecast

PREGENERATE_JOB = "pregenerate_outfit"

# Outfits are prepared early in the user's morning, before the app is opened.
WINDOW_START_HOUR = 4
WINDOW_END_HOUR = 6
# People who stopped opening the app do not get outfits prepared for them.
ACTIVE_WITHIN = dt.timedelta(days=7)

FRIDAY, SATURDAY = 4, 5


def default_occasion(local_time: dt.datetime) -> Occasion:
    # Must match defaultOccasion() in mobile/lib/outfits.ts, or the prepared outfit is not shown.
    weekday = local_time.weekday()
    if weekday < SATURDAY and local_time.hour < 17:
        return Occasion.WORK
    if weekday in (FRIDAY, SATURDAY) and local_time.hour >= 17:
        return Occasion.NIGHT_OUT
    return Occasion.CASUAL


def _local_time(user: User, now: dt.datetime) -> dt.datetime:
    return now + dt.timedelta(minutes=user.utc_offset_minutes or 0)


def enqueue_due(db: Session, now: dt.datetime | None = None) -> int:
    now = now or dt.datetime.now(dt.UTC)
    users = db.scalars(
        select(User).where(
            User.utc_offset_minutes.is_not(None), User.last_seen_at >= now - ACTIVE_WITHIN
        )
    )

    enqueued = 0
    for user in users:
        local_time = _local_time(user, now)
        if not WINDOW_START_HOUR <= local_time.hour < WINDOW_END_HOUR:
            continue
        day = local_time.date()
        payload = {"user_id": str(user.id), "day": day.isoformat()}
        already_done = db.scalar(
            select(Outfit.id).where(Outfit.user_id == user.id, Outfit.day == day).limit(1)
        )
        already_queued = db.scalar(
            select(Job.id)
            .where(
                Job.kind == PREGENERATE_JOB,
                Job.payload == payload,
                Job.status.in_((JobStatus.QUEUED, JobStatus.RUNNING)),
            )
            .limit(1)
        )
        if already_done or already_queued:
            continue
        jobs.enqueue(db, PREGENERATE_JOB, payload)
        enqueued += 1

    db.commit()
    return enqueued


def pregenerate_outfit(db: Session, payload: jobs.Payload) -> None:
    user = db.get(User, uuid.UUID(payload["user_id"]))
    if user is None:
        return
    day = dt.date.fromisoformat(payload["day"])
    morning = dt.datetime.combine(day, dt.time(hour=7))

    forecast = None
    if user.latitude is not None and user.longitude is not None:
        forecast = get_forecast(user.latitude, user.longitude, day)
    try:
        service.get_today(db, user, day, default_occasion(morning), forecast)
    except service.NotEnoughGarmentsError:
        # Nothing to prepare yet; the app explains what is missing when it opens.
        return


jobs.register(PREGENERATE_JOB, jobs.JobHandler(run=pregenerate_outfit))
