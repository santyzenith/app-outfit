import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Job, JobStatus

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RETRY_DELAY = timedelta(seconds=30)
# A job still "running" after this long belonged to a worker that died.
STALE_AFTER = timedelta(minutes=10)

Payload = dict[str, Any]


@dataclass(frozen=True)
class JobHandler:
    run: Callable[[Session, Payload], None]
    on_give_up: Callable[[Session, Payload], None] | None = None


_handlers: dict[str, JobHandler] = {}


def register(kind: str, handler: JobHandler) -> None:
    _handlers[kind] = handler


def enqueue(db: Session, kind: str, payload: Payload) -> Job:
    # No commit here: the job is saved together with whatever the caller is saving.
    job = Job(kind=kind, payload=payload)
    db.add(job)
    return job


def run_next_job(db: Session) -> bool:
    now = datetime.now(UTC)
    job = db.scalar(
        select(Job)
        .where(Job.status == JobStatus.QUEUED, Job.run_after <= now)
        .order_by(Job.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if job is None:
        return False

    job.status = JobStatus.RUNNING
    job.attempts += 1
    job.locked_at = now
    db.commit()

    handler = _handlers[job.kind]
    try:
        handler.run(db, job.payload)
        job.status = JobStatus.DONE
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("job %s (%s) failed on attempt %s", job.id, job.kind, job.attempts)
        job.last_error = repr(exc)
        if job.attempts < MAX_ATTEMPTS:
            job.status = JobStatus.QUEUED
            job.run_after = datetime.now(UTC) + RETRY_DELAY * job.attempts
        else:
            job.status = JobStatus.FAILED
            if handler.on_give_up is not None:
                handler.on_give_up(db, job.payload)
        db.commit()
    return True


def requeue_stale_jobs(db: Session) -> int:
    result = db.execute(
        update(Job)
        .where(Job.status == JobStatus.RUNNING, Job.locked_at < datetime.now(UTC) - STALE_AFTER)
        .values(status=JobStatus.QUEUED, locked_at=None)
    )
    db.commit()
    return result.rowcount
