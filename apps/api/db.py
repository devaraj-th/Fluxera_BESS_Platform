from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from apps.api.settings import get_settings


class Base(DeclarativeBase):
    pass


_engine = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = get_settings().database_url
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    return _engine


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=None)


def get_session() -> Generator[Session, None, None]:
    SessionLocal.configure(bind=get_engine())
    with SessionLocal() as session:
        yield session
