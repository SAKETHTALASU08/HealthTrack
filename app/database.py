"""Database engine, session factory, and declarative base.

The database URL is read from :data:`app.config.settings` so that
tests can substitute an in-memory SQLite URL without touching the
filesystem.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    # Required for SQLite: allows the same connection across threads.
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def get_db():
    """Yield a database session and ensure it is closed after use.

    Intended for FastAPI dependency injection via ``Depends(get_db)``.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
