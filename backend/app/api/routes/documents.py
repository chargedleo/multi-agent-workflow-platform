"""Document management API routes for uploading, listing, viewing, and deleting documents."""

import uuid
from typing import Any, Dict
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger
from backend.app.db.session import get_db
from backend.app.documents.schemas import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentSummary,
    DocumentUploadResponse,
)
from backend.app.documents.service import DocumentService

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a document",
    description="Uploads a PDF, plain text, or Markdown document, extracts text with page awareness, generates embeddings, and indexes chunks in FAISS.",
)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload and process a document file into the vector knowledge base."""
    filename = file.filename or "uploaded_document"
    settings = get_settings()

    # 1. Validate file extension
    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported formats are: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # 2. Read file content
    try:
        content = await file.read()
    except Exception as read_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(read_err)}",
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    # 3. Check file size
    max_bytes = settings.MAX_DOCUMENT_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_DOCUMENT_SIZE_MB}MB.",
        )

    # 4. Ingest document via DocumentService
    try:
        doc = await DocumentService.ingest_document(
            db=session,
            file_bytes=content,
            original_filename=filename,
            content_type=file.content_type or "application/octet-stream",
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        logger.error(f"Error during document ingestion: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {str(exc)}",
        )

    return DocumentUploadResponse(
        document_id=doc.id,
        filename=doc.original_filename,
        status=doc.status,
        page_count=doc.page_count,
        chunk_count=doc.chunk_count,
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List ingested documents",
    description="Returns a paginated list of documents with metadata, page counts, and indexing status.",
)
async def list_documents(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """Retrieve paginated list of documents."""
    items, total = await DocumentService.list_documents(
        db=session,
        page=page,
        page_size=page_size,
    )

    summaries = [
        DocumentSummary(
            document_id=doc.id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            content_type=doc.content_type,
            file_size=doc.file_size,
            status=doc.status,
            page_count=doc.page_count,
            chunk_count=doc.chunk_count,
            checksum=doc.checksum,
            created_at=doc.created_at,
        )
        for doc in items
    ]

    return DocumentListResponse(
        items=summaries,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get document details",
    description="Returns detailed metadata and chunk summary for a specific document.",
)
async def get_document(
    document_id: str,
    session: AsyncSession = Depends(get_db),
) -> DocumentDetailResponse:
    """Retrieve full document details by ID."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document UUID format: '{document_id}'",
        )

    doc = await DocumentService.get_document(db=session, document_id=doc_uuid)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    return DocumentDetailResponse(
        document_id=doc.id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        content_type=doc.content_type,
        file_size=doc.file_size,
        checksum=doc.checksum,
        status=doc.status,
        page_count=doc.page_count,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
        metadata=doc.metadata_json or {},
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a document",
    description="Deletes a document from the database, deletes stored file, and removes associated vectors from FAISS.",
)
async def delete_document(
    document_id: str,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Delete a document and purge its vectors from FAISS."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document UUID format: '{document_id}'",
        )

    deleted = await DocumentService.delete_document(db=session, document_id=doc_uuid)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    return {"status": "deleted", "document_id": str(document_id)}
