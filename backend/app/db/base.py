"""SQLAlchemy Declarative Base and JSON type definition."""

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import JSON

# JSONB on PostgreSQL; JSON on other dialects (such as SQLite for fast isolated tests)
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy database models."""
    pass
