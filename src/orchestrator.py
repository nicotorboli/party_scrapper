from __future__ import annotations

import logging
from typing import Sequence

from src.filters.city_filter import CityFilter
from src.models.event import Event
from src.notifiers.base_notifier import BaseNotifier
from src.scrapers.base_scraper import BaseScraper
from src.storage.event_repository import EventRepository

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Facade that coordinates scrapers → city filter → deduplication → notifiers.
    No component knows about the others; all wiring happens here.
    """

    def __init__(
        self,
        scrapers: Sequence[BaseScraper],
        city_filter: CityFilter,
        repository: EventRepository,
        notifiers: Sequence[BaseNotifier],
    ) -> None:
        self._scrapers = scrapers
        self._city_filter = city_filter
        self._repository = repository
        self._notifiers = notifiers

    def run(self) -> int:
        """Execute one full scrape cycle. Returns number of new events notified."""
        all_events: list[Event] = []
        for scraper in self._scrapers:
            logger.info("Running scraper: %s", scraper.source_name)
            all_events.extend(scraper.scrape())

        local_events = self._city_filter.filter(all_events)
        logger.info(
            "Total events: %d | After city filter: %d",
            len(all_events),
            len(local_events),
        )

        # Deduplicate in-memory (same event from multiple scrapers)
        unique_events = list({e.id: e for e in local_events}.values())

        notified = 0
        for event in unique_events:
            if self._repository.is_seen(event.id):
                continue
            for notifier in self._notifiers:
                notifier.notify(event)
            self._repository.mark_seen(event)
            notified += 1

        logger.info("New events notified: %d", notified)
        return notified
