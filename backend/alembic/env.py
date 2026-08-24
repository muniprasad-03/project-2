from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

from app.core.config import settings
from app.core.database import Base

# Import all SQLAlchemy models so they are registered with Base.metadata.
from app.models import db_models  # noqa: F401


# Alembic Config object.
config = context.config


# Configure Python logging from alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# SQLAlchemy metadata used by Alembic for autogenerate.
target_metadata = Base.metadata


def get_database_url() -> str:
    """
    Get the PostgreSQL database URL from the application's settings.

    Alembic should use the same database configuration as the FastAPI
    application rather than storing credentials in alembic.ini.
    """
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """
    Run migrations without creating a database connection.

    This generates SQL statements that can be inspected or executed later.
    """
    url = get_database_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations using an active database connection.
    """
    configuration = config.get_section(config.config_ini_section, {})

    # Use the application's database URL instead of storing credentials
    # inside alembic.ini.
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()