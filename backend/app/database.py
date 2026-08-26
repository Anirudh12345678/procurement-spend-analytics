from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def create_database_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_settings().database_url
    return create_engine(url, pool_pre_ping=True)


engine = create_database_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        with session.begin():
            yield session
    finally:
        session.close()
