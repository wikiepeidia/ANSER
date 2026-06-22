import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# Make project root importable so core.db.models resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Load DB URL from .env
_raw = os.environ["POSTGRES_URL"]
DB_URL = _raw.replace("postgresql://", "postgresql+psycopg2://", 1)
config.set_main_option("sqlalchemy.url", DB_URL)

# Import all models so Alembic sees them for autogenerate
from core.db.models import IoTEvent  # noqa: F401
from core.db.connection import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
