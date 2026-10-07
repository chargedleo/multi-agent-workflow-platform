"""Pydantic schemas for document ingestion, storage, and vector retrieval."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Response returned upon initiating/completing document ingestion."""

    document_id: uuid.UUID = Field(..., description="Unique document UUID")
    filename: str = Field(..., description="Stored internal or original filename")
    status: str = Field(..., description="Ingestion status: COMPLETED, PENDING, FAILED")
    page_count: int = Field(default=1, description="Total pages extracted from document")
    chunk_count: int = Field(default=0, description="Total chunks generated and indexed")


class DocumentSummary(BaseModel):
    """Summary representation for document listings."""

    document_id: uuid.UUID = Field(..., description="Unique document UUID")
    filename: str = Field(..., description="Stored filename")
    original_filename: str = Field(..., description="Original uploaded filename")
    content_type: str = Field(..., description="MIME content type")
    file_size: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="Ingestion lifecycle status")
    page_count: int = Field(default=1, description="Number of pages")
    chunk_count: int = Field(default=0, description="Number of chunks")
    checksum: str = Field(..., description="SHA-256 digest")
    created_at: datetime = Field(..., description="Timestamp of upload")


class DocumentListResponse(BaseModel):
    """Paginated collection of ingested documents."""

    items: List[DocumentSummary] = Field(default_factory=list, description="Page of documents")
    page: int = Field(default=1, ge=1, description="Current page number")
    page_size: int = Field(default=20, ge=1, description="Items per page")
    total: int = Field(default=0, ge=0, description="Total document count")


class DocumentDetailResponse(BaseModel):
    """Detailed metadata for a single document."""

    document_id: uuid.UUID = Field(..., description="Unique document UUID")
    filename: str = Field(..., description="Stored filename")
    original_filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME content type")
    file_size: int = Field(..., description="File size in bytes")
    checksum: str = Field(..., description="SHA-256 checksum")
    status: str = Field(..., description="Ingestion status")
    page_count: int = Field(..., description="Page count")
    chunk_count: int = Field(..., description="Chunk count")
    error_message: Optional[str] = Field(default=None, description="Error explanation if ingestion failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom document metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class RetrievedChunk(BaseModel):
    """Individual retrieved text segment returned by vector search."""

    chunk_id: str = Field(..., description="UUID string of the source chunk")
    document_id: str = Field(..., description="UUID string of the parent document")
    filename: str = Field(..., description="Original or stored filename")
    content: str = Field(..., description="Raw text content of the chunk")
    page_number: int = Field(default=1, description="Page number where content originated")
    similarity_score: float = Field(..., description="Cosine similarity / inner product score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")


class RetrievalResult(BaseModel):
    """Structured output from vector similarity search."""

    query: str = Field(..., description="The query string used for retrieval")
    results: List[RetrievedChunk] = Field(default_factory=list, description="Top-k retrieved chunks")


class SourceCitation(BaseModel):
    """Attribution citation linking a response statement to a specific document chunk."""

    document_id: str = Field(..., description="Document UUID string")
    filename: str = Field(..., description="Source filename")
    page_number: int = Field(default=1, description="Source page number")
    chunk_id: str = Field(..., description="Source chunk UUID string")
