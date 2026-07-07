"""
Alembic migration environment.
Reads DATABASE_URL from application settings so migrations
always use the same database as the running application.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure project root is on the path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402
from database import Base  # noqa: E402  (imports all SQLAlchemy models)

# Alembic Config object — provides access to values in alembic.ini
config = context.config

# Wire up logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The MetaData for 'autogenerate' support
target_metadata = Base.metadata

# Override sqlalchemy.url with the value from our settings
# (never commit credentials to alembic.ini)
config.set_main_option(
    "sqlalchemy.url",
    settings.database_url.replace("postgres://", "postgresql://", 1),
)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode (no live DB connection).
    Produces a SQL script that can be applied manually.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (live DB connection).
    Used by `alembic upgrade head`.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
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
