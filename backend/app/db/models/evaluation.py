"""SQLAlchemy database models for evaluation engine persistence (Milestone 9A)."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, JSON_TYPE


class EvaluationRun(Base):
    """Database record representing an execution of an evaluation benchmark."""

    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=uuid.uuid4,
    )
    dataset_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    dataset_checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="metric_only")
    application_version: Mapped[str] = mapped_column(String(32), nullable=False, default="0.1.0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    configuration_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE, default=dict)
    aggregate_metrics: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE, default=dict)
    summary: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE, default=dict)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # One-to-many relationship with case results
    case_results: Mapped[List["EvaluationCaseResultRecord"]] = relationship(
        "EvaluationCaseResultRecord",
        back_populates="evaluation_run",
        cascade="all, delete-orphan",
        order_by="EvaluationCaseResultRecord.created_at",
    )


class EvaluationCaseResultRecord(Base):
    """Database entity representing an individual benchmark case outcome."""

    __tablename__ = "evaluation_case_results"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=uuid.uuid4,
    )
    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    case_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    associated_workflow_run_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPLETED")
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Serialized metric outputs
    metric_results: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE, default=dict)
    safe_error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship back to EvaluationRun
    evaluation_run: Mapped["EvaluationRun"] = relationship(
        "EvaluationRun",
        back_populates="case_results",
    )


# Indexes for rapid retrieval
Index("ix_eval_case_results_run_case", EvaluationCaseResultRecord.evaluation_run_id, EvaluationCaseResultRecord.case_id)
