from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


# ---------------------------------------------------------------------------
# Database URL
# ---------------------------------------------------------------------------

DATABASE_URL = settings.DATABASE_URL

# Supabase provides a PostgreSQL URL.
# SQLAlchemy with psycopg2 expects the postgresql:// form.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1,
    )


# ---------------------------------------------------------------------------
# SQLAlchemy Engine
# ---------------------------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)


# ---------------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Declarative Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    """

    pass


# ---------------------------------------------------------------------------
# FastAPI Database Dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    Provide a database session to a FastAPI request.

    The session is always closed after the request finishes.
    """
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Database Connectivity Check
# ---------------------------------------------------------------------------

def check_database_connection() -> bool:
    """
    Check whether the configured Supabase PostgreSQL database
    is reachable.

    Returns:
        True when SELECT 1 succeeds.

    Raises:
        Exception when the database cannot be reached.
    """
    from sqlalchemy import text

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return True


# ---------------------------------------------------------------------------
# Local execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        check_database_connection()

        print("Database connection successful.")

    except Exception as exc:
        print("Database connection failed.")
        print(f"Error: {exc}")
        raise