"""SQLAlchemy model for document chunks."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, JSON_TYPE

if TYPE_CHECKING:
    from backend.app.db.models.document import Document


class DocumentChunk(Base):
    """Database entity representing a segmented text chunk from an ingested document."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    start_char: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_char: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",
        JSON_TYPE,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks",
    )

    __table_args__ = (
        Index("ix_document_chunks_document_id_chunk_index", "document_id", "chunk_index"),
    )
