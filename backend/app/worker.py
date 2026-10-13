import logging
import signal
import time

import app.garments.processing  # noqa: F401  (registers its job handler)
from app.db import SessionLocal
from app.jobs import requeue_stale_jobs, run_next_job

logger = logging.getLogger(__name__)

IDLE_SLEEP_SECONDS = 1.0
STALE_CHECK_SECONDS = 60.0

_stopping = False


def _stop(*_: object) -> None:
    global _stopping
    _stopping = True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    logger.info("worker started")

    last_stale_check = 0.0
    while not _stopping:
        with SessionLocal() as db:
            if time.monotonic() - last_stale_check > STALE_CHECK_SECONDS:
                requeue_stale_jobs(db)
                last_stale_check = time.monotonic()
            worked = run_next_job(db)
        if not worked:
            time.sleep(IDLE_SLEEP_SECONDS)

    logger.info("worker stopped")


if __name__ == "__main__":
    main()
