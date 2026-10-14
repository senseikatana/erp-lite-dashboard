"""SQLAlchemy engine, session factory and declarative base."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


def _build_engine():
    kwargs: dict = {"echo": settings.sql_echo}
    if settings.is_sqlite:
        # Streamlit and FastAPI both open connections from different threads.
        # SQLite serialises writes, so this flag keeps the driver from raising
        # "database is locked" under concurrent requests.
        kwargs["connect_args"] = {"check_same_thread": False}

        if settings.is_in_memory:
            # A plain in-memory SQLite database gives every pooled connection
            # its own empty copy, so the schema created at startup would vanish
            # for the next request. StaticPool pins a single connection for the
            # lifetime of the engine, which is what the tests rely on.
            kwargs["poolclass"] = StaticPool

    return create_engine(settings.database_url, **kwargs)


engine = _build_engine()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


if settings.is_sqlite:

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        """Enforce foreign keys.

        SQLite ships with foreign key enforcement switched off. Without this
        the application would happily write orphaned order lines.
        """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session.

    The session is always closed, including when the request raises.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()