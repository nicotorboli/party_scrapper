from abc import ABC, abstractmethod

from src.models.event import Event


class BaseNotifier(ABC):
    """Observer interface — add new channels by subclassing this."""

    @abstractmethod
    def notify(self, event: Event) -> None: ...
