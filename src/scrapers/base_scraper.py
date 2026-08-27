from abc import ABC, abstractmethod

from src.models.event import Event


class BaseScraper(ABC):
    """Strategy interface — every site implements this."""

    @property
    @abstractmethod
    def source_name(self) -> str: ...

    @abstractmethod
    def scrape(self) -> list[Event]:
        """Fetch and parse events from the site. Must not raise."""
        ...
