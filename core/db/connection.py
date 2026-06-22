"""
Database connection for NeonDB (PostgreSQL).
Schema is managed exclusively by Alembic — do NOT create or alter tables manually.
Run migrations with: alembic upgrade head
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

_raw_url = os.environ["POSTGRES_URL"]
# SQLAlchemy requires postgresql+psycopg2:// driver prefix
DB_URL = _raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
