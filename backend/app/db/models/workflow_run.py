"""SQLAlchemy model for workflow runs."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import BigInteger, DateTime, Float, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, JSON_TYPE

if TYPE_CHECKING:
    from backend.app.db.models.workflow_step import WorkflowStep


class WorkflowRun(Base):
    """Database entity representing a single multi-agent workflow execution run."""

    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=uuid.uuid4,
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        nullable=False,
        index=True,
    )
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # Agent output and synthesis attributes
    final_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_points: Mapped[Optional[List[str]]] = mapped_column(JSON_TYPE, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    plan: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)
    research_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)
    errors: Mapped[List[str]] = mapped_column(JSON_TYPE, default=list)

    # Generic metadata mapping
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",
        JSON_TYPE,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # One-to-many relationship with steps
    steps: Mapped[List["WorkflowStep"]] = relationship(
        "WorkflowStep",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="WorkflowStep.step_order",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_workflow_runs_status_created_at", "status", "created_at"),
    )
