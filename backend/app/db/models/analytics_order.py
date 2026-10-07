"""SQLAlchemy model for analytics orders dataset."""

import uuid
from sqlalchemy import Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class AnalyticsOrder(Base):
    """Database entity representing an order in the approved analytics dataset."""

    __tablename__ = "analytics_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=uuid.uuid4,
    )
    order_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        unique=True,
        index=True,
    )
    order_date: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        index=True,
    )
    customer: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    region: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    product: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    unit_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    revenue: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
