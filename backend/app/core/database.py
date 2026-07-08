"""
app/core/database.py
SQLAlchemy async-compatible engine, session factory, and Base for all models.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import get_settings

settings = get_settings()

# Synchronous engine (psycopg2 driver)
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,          # reconnect on stale connections
    pool_size=10,
    max_overflow=20,
    echo=settings.app_env == "development",  # log SQL in dev only
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


# ---------------------------------------------------------------------------
# FastAPI dependency — yields a DB session and guarantees cleanup
# ---------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
