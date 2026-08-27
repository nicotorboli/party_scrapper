import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.event import Base


@pytest.fixture
def in_memory_session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)
