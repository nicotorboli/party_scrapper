from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from src.models.event import Base

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "events.db"


def build_engine(db_url: str | None = None) -> Engine:
    if db_url is None:
        _DB_PATH.parent.mkdir(exist_ok=True)
        db_url = f"sqlite:///{_DB_PATH}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
