import unicodedata
from typing import Sequence

from src.models.event import Event


def _normalize(text: str) -> str:
    """Lowercase + remove diacritics for fuzzy matching."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


class CityFilter:
    def __init__(self, keywords: Sequence[str]) -> None:
        self._keywords = [_normalize(k) for k in keywords]

    def matches(self, event: Event) -> bool:
        haystack = _normalize(f"{event.city} {event.venue}")
        return any(kw in haystack for kw in self._keywords)

    def filter(self, events: Sequence[Event]) -> list[Event]:
        return [e for e in events if self.matches(e)]
