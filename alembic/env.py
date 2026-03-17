from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# Ensure project root is on PYTHONPATH so that `db` package is importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))

# Import metadata and DB config from the app
from db.base import Base  # noqa: E402
from db import models as _models  # noqa: F401, E402  # ensure models are imported
from db.config import get_database_url  # noqa: E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# If DATABASE_URL is set, prefer it over the value in alembic.ini
database_url = os.getenv("DATABASE_URL")
if database_url:
  config.set_main_option("sqlalchemy.url", database_url)
else:
  # Fallback to application DB config (will raise if env is not configured)
  config.set_main_option("sqlalchemy.url", get_database_url())

# Interpret the config file for Python logging.
if config.config_file_name is not None:
  fileConfig(config.config_file_name)

# Set target metadata for 'autogenerate' support.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
  """Run migrations in 'offline' mode."""
  url = config.get_main_option("sqlalchemy.url")
  context.configure(
    url=url,
    target_metadata=target_metadata,
    literal_binds=True,
    dialect_opts={"paramstyle": "named"},
  )

  with context.begin_transaction():
    context.run_migrations()


def run_migrations_online() -> None:
  """Run migrations in 'online' mode."""
  connectable = engine_from_config(
    config.get_section(config.config_ini_section, {}),
    prefix="sqlalchemy.",
    poolclass=pool.NullPool,
  )

  with connectable.connect() as connection:
    context.configure(
      connection=connection,
      target_metadata=target_metadata,
    )

    with context.begin_transaction():
      context.run_migrations()


if context.is_offline_mode():
  run_migrations_offline()
else:
  run_migrations_online()

