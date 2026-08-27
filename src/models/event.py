from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


@dataclass
class Event:
    title: str
    date: datetime
    venue: str
    city: str
    source: str
    ticket_url: str
    id: str = field(init=False)

    def __post_init__(self) -> None:
        raw = f"{self.source}:{self.title}:{self.date.date()}"
        self.id = hashlib.sha256(raw.encode()).hexdigest()[:16]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Event) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class SeenEvent(Base):
    __tablename__ = "seen_events"

    event_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    source = Column(String, nullable=False)
    notified_at = Column(DateTime, nullable=False, default=datetime.utcnow)
