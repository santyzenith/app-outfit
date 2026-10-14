import logging
import signal
import time

import app.garments.processing  # noqa: F401  (registers its job handler)
import app.inspirations.processing  # noqa: F401
from app.db import SessionLocal
from app.jobs import requeue_stale_jobs, run_next_job
from app.outfits.pregeneration import enqueue_due

logger = logging.getLogger(__name__)

IDLE_SLEEP_SECONDS = 1.0
# How often the worker looks for stuck jobs and for outfits to prepare.
HOUSEKEEPING_SECONDS = 60.0

_stopping = False


def _stop(*_: object) -> None:
    global _stopping
    _stopping = True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    logger.info("worker started")

    last_housekeeping = 0.0
    while not _stopping:
        with SessionLocal() as db:
            if time.monotonic() - last_housekeeping > HOUSEKEEPING_SECONDS:
                requeue_stale_jobs(db)
                enqueue_due(db)
                last_housekeeping = time.monotonic()
            worked = run_next_job(db)
        if not worked:
            time.sleep(IDLE_SLEEP_SECONDS)

    logger.info("worker stopped")


if __name__ == "__main__":
    main()
