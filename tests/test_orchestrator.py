from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.filters.city_filter import CityFilter
from src.models.event import Event
from src.orchestrator import Orchestrator
from src.storage.event_repository import EventRepository


def make_event(title: str, city: str = "Buenos Aires") -> Event:
    return Event(
        title=title,
        date=datetime(2025, 6, 15),
        venue="Crobar",
        city=city,
        source="test",
        ticket_url="https://example.com",
    )


def test_orchestrator_notifies_new_local_events(in_memory_session_factory):
    scraper = MagicMock()
    scraper.source_name = "test"
    scraper.scrape.return_value = [
        make_event("CABA Party"),
        make_event("Córdoba Party", city="Córdoba"),
    ]

    city_filter = CityFilter(["buenos aires", "caba"])
    repo = EventRepository(in_memory_session_factory)
    notifier = MagicMock()

    orch = Orchestrator([scraper], city_filter, repo, [notifier])
    count = orch.run()

    assert count == 1
    notifier.notify.assert_called_once()
    notified_event = notifier.notify.call_args[0][0]
    assert notified_event.title == "CABA Party"


def test_orchestrator_deduplicates_across_runs(in_memory_session_factory):
    scraper = MagicMock()
    scraper.source_name = "test"
    event = make_event("Bresh CABA")
    scraper.scrape.return_value = [event]

    city_filter = CityFilter(["buenos aires"])
    repo = EventRepository(in_memory_session_factory)
    notifier = MagicMock()

    orch = Orchestrator([scraper], city_filter, repo, [notifier])
    orch.run()
    orch.run()  # second run — same event, already seen

    assert notifier.notify.call_count == 1


def test_orchestrator_deduplicates_same_event_from_multiple_scrapers(in_memory_session_factory):
    event = make_event("Wasabi Fest")
    scraper_a = MagicMock()
    scraper_a.source_name = "scraper_a"
    scraper_a.scrape.return_value = [event]

    scraper_b = MagicMock()
    scraper_b.source_name = "scraper_b"
    scraper_b.scrape.return_value = [event]  # same event id

    city_filter = CityFilter(["buenos aires"])
    repo = EventRepository(in_memory_session_factory)
    notifier = MagicMock()

    orch = Orchestrator([scraper_a, scraper_b], city_filter, repo, [notifier])
    count = orch.run()

    assert count == 1
    assert notifier.notify.call_count == 1
