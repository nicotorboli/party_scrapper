from datetime import datetime

import pytest

from src.filters.city_filter import CityFilter
from src.models.event import Event

KEYWORDS = ["buenos aires", "caba", "palermo", "quilmes", "zona sur"]


def make_event(city: str, venue: str = "") -> Event:
    return Event(
        title="Test Event",
        date=datetime(2025, 6, 15),
        venue=venue,
        city=city,
        source="test",
        ticket_url="https://example.com",
    )


def test_matches_exact_city():
    f = CityFilter(KEYWORDS)
    assert f.matches(make_event("Buenos Aires"))


def test_matches_accent_insensitive():
    f = CityFilter(KEYWORDS)
    # "palermo" keyword vs "Palermo" city
    assert f.matches(make_event("Palermo"))


def test_matches_city_in_venue():
    f = CityFilter(KEYWORDS)
    assert f.matches(make_event("", venue="Club Quilmes"))


def test_rejects_other_city():
    f = CityFilter(KEYWORDS)
    assert not f.matches(make_event("Córdoba"))


def test_rejects_empty():
    f = CityFilter(KEYWORDS)
    assert not f.matches(make_event("", venue=""))


def test_filter_returns_only_matching():
    f = CityFilter(KEYWORDS)
    events = [
        make_event("Buenos Aires"),
        make_event("Mendoza"),
        make_event("Quilmes"),
        make_event("Rosario"),
    ]
    result = f.filter(events)
    assert len(result) == 2
    assert all(f.matches(e) for e in result)
