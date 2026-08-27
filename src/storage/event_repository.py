from datetime import datetime, UTC

from sqlalchemy.orm import sessionmaker, Session

from src.models.event import Event, SeenEvent


class EventRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    def is_seen(self, event_id: str) -> bool:
        with self._factory() as session:
            return session.get(SeenEvent, event_id) is not None

    def mark_seen(self, event: Event) -> None:
        with self._factory() as session:
            seen = SeenEvent(
                event_id=event.id,
                title=event.title,
                source=event.source,
                notified_at=datetime.now(UTC),
            )
            session.merge(seen)
            session.commit()

    def get_all_seen_ids(self) -> set[str]:
        with self._factory() as session:
            rows = session.query(SeenEvent.event_id).all()
            return {r.event_id for r in rows}
