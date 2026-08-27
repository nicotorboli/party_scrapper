from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


def start(orchestrator: Orchestrator, interval_hours: int = 6) -> None:
    """Run orchestrator immediately, then every `interval_hours` hours."""
    scheduler = BlockingScheduler(timezone="America/Argentina/Buenos_Aires")
    scheduler.add_job(
        func=orchestrator.run,
        trigger=IntervalTrigger(hours=interval_hours),
        next_run_time=datetime.now(),
        id="party_scrapper",
        name="Party event scrapper",
        misfire_grace_time=300,
    )
    logger.info("Scheduler started — interval: %dh", interval_hours)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")
