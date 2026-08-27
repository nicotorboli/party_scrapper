from datetime import datetime

import pytest

from src.models.event import Event
from src.storage.event_repository import EventRepository


def make_event(title: str = "Bresh CABA") -> Event:
    return Event(
        title=title,
        date=datetime(2025, 6, 15),
        venue="Crobar",
        city="Buenos Aires",
        source="bresh",
        ticket_url="https://bresh.com/events/1",
    )


def test_event_not_seen_initially(in_memory_session_factory):
    repo = EventRepository(in_memory_session_factory)
    event = make_event()
    assert not repo.is_seen(event.id)


def test_mark_seen_persists(in_memory_session_factory):
    repo = EventRepository(in_memory_session_factory)
    event = make_event()
    repo.mark_seen(event)
    assert repo.is_seen(event.id)


def test_mark_seen_idempotent(in_memory_session_factory):
    repo = EventRepository(in_memory_session_factory)
    event = make_event()
    repo.mark_seen(event)
    repo.mark_seen(event)  # should not raise
    assert repo.is_seen(event.id)


def test_get_all_seen_ids(in_memory_session_factory):
    repo = EventRepository(in_memory_session_factory)
    e1 = make_event("Event A")
    e2 = make_event("Event B")
    repo.mark_seen(e1)
    repo.mark_seen(e2)
    ids = repo.get_all_seen_ids()
    assert e1.id in ids
    assert e2.id in ids
