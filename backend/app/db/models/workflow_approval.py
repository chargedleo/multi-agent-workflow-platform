"""SQLAlchemy model for workflow human approvals."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, JSON_TYPE

if TYPE_CHECKING:
    from backend.app.db.models.workflow_run import WorkflowRun


class WorkflowApproval(Base):
    """Database entity representing a human-in-the-loop approval request and decision."""

    __tablename__ = "workflow_approvals"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=uuid.uuid4,
    )
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
        index=True,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    decided_by: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    decision: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    feedback: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    revision_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
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

    # Relationship to parent workflow run
    run: Mapped["WorkflowRun"] = relationship(
        "WorkflowRun",
        back_populates="approvals",
    )

    __table_args__ = (
        Index("ix_workflow_approvals_status_requested_at", "status", "requested_at"),
    )
