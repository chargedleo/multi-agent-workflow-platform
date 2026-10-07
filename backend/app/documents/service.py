"""Document service handling ingestion, deduplication, chunking, indexing, and deletion."""

import hashlib
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger
from backend.app.db.models.document import Document
from backend.app.db.models.document_chunk import DocumentChunk
from backend.app.documents.chunking.splitter import DocumentSplitter
from backend.app.documents.embeddings.provider import get_embedding_provider
from backend.app.documents.loaders import get_document_loader
from backend.app.documents.vectorstore.faiss_store import get_vector_store

logger = get_logger(__name__)


class DocumentService:
    """Service layer managing document ingestion and vector synchronization."""

    @staticmethod
    async def ingest_document(
        db: AsyncSession,
        file_bytes: bytes,
        original_filename: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """Execute end-to-end document ingestion pipeline.

        1. Validates file format and size limits.
        2. Computes SHA-256 for duplicate avoidance.
        3. Persists file to secure local disk location.
        4. Extracts text pages preserving page numbering.
        5. Segments text into structured chunks.
        6. Generates embeddings and updates FAISS index.
        7. Persists document and chunk metadata in PostgreSQL.
        """
        settings = get_settings()
        meta = metadata or {}

        # 1. Validation
        max_bytes = settings.MAX_DOCUMENT_SIZE_MB * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise ValueError(
                f"File size exceeds maximum limit of {settings.MAX_DOCUMENT_SIZE_MB}MB "
                f"({len(file_bytes)} bytes uploaded)."
            )

        if not file_bytes:
            raise ValueError("Uploaded file is empty (0 bytes).")

        # Validate format through loader factory
        loader = get_document_loader(original_filename)

        # 2. Duplicate Detection via SHA-256
        checksum = hashlib.sha256(file_bytes).hexdigest()
        existing_stmt = select(Document).where(
            Document.checksum == checksum,
            Document.status == "COMPLETED",
        )
        existing_res = await db.execute(existing_stmt)
        existing_doc = existing_res.scalar_one_or_none()
        if existing_doc:
            logger.info(
                f"Document with checksum {checksum[:8]}... already ingested as ID {existing_doc.id}. "
                "Returning existing record."
            )
            # Ensure vectors are present in FAISS store even if index was reloaded or cleared
            vector_store = get_vector_store()
            has_doc = any(m.get("document_id") == str(existing_doc.id) for m in vector_store._metadata)
            if not has_doc:
                existing_full = await DocumentService.get_document(db, existing_doc.id)
                if existing_full and existing_full.chunks:
                    provider = get_embedding_provider()
                    texts = [c.content for c in existing_full.chunks]
                    vecs = provider.embed_documents(texts)
                    metas = [
                        {
                            "chunk_id": str(c.id),
                            "document_id": str(existing_doc.id),
                            "filename": existing_doc.original_filename,
                            "page_number": c.page_number,
                            "content": c.content,
                        }
                        for c in existing_full.chunks
                    ]
                    vector_store.add_vectors(vecs, metas)
            return existing_doc

        # 3. Secure disk storage
        doc_id = uuid.uuid4()
        file_ext = Path(original_filename).suffix.lower()
        storage_filename = f"{doc_id}{file_ext}"

        storage_dir = Path(settings.DOCUMENT_STORAGE_PATH)
        storage_dir.mkdir(parents=True, exist_ok=True)
        stored_path = storage_dir / storage_filename

        with open(stored_path, "wb") as f:
            f.write(file_bytes)

        # 4. Create Initial DB Record
        doc = Document(
            id=doc_id,
            filename=storage_filename,
            original_filename=original_filename,
            content_type=content_type,
            file_size=len(file_bytes),
            checksum=checksum,
            status="PROCESSING",
            page_count=1,
            chunk_count=0,
            metadata_json=meta,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        try:
            # 5. Extract pages
            pages = loader.load(stored_path)
            doc.page_count = max(1, len(pages))

            # 6. Split into chunks
            splitter = DocumentSplitter(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )
            raw_chunks = splitter.split_pages(pages)

            db_chunks: List[DocumentChunk] = []
            chunk_vectors: List[List[float]] = []
            chunk_metadata_list: List[Dict[str, Any]] = []

            if raw_chunks:
                embedding_provider = get_embedding_provider()
                chunk_texts = [c.content for c in raw_chunks]
                chunk_vectors = embedding_provider.embed_documents(chunk_texts)

                for chunk_data in raw_chunks:
                    chunk_id = uuid.uuid4()
                    db_chunk = DocumentChunk(
                        id=chunk_id,
                        document_id=doc.id,
                        chunk_index=chunk_data.chunk_index,
                        content=chunk_data.content,
                        page_number=chunk_data.page_number,
                        start_char=chunk_data.start_char,
                        end_char=chunk_data.end_char,
                        token_count=chunk_data.token_count,
                        metadata_json=chunk_data.metadata,
                    )
                    db_chunks.append(db_chunk)

                    chunk_metadata_list.append(
                        {
                            "chunk_id": str(chunk_id),
                            "document_id": str(doc.id),
                            "filename": original_filename,
                            "page_number": chunk_data.page_number,
                            "content": chunk_data.content,
                        }
                    )

                # 7. Index in FAISS
                vector_store = get_vector_store()
                vector_store.add_vectors(chunk_vectors, chunk_metadata_list)

                db.add_all(db_chunks)

            doc.chunk_count = len(db_chunks)
            doc.status = "COMPLETED"
            doc.error_message = None
            await db.commit()
            await db.refresh(doc)

            logger.info(
                f"Successfully ingested document '{original_filename}' (ID: {doc.id}): "
                f"{doc.page_count} pages, {doc.chunk_count} chunks indexed."
            )
            return doc

        except Exception as exc:
            logger.error(f"Failed to ingest document '{original_filename}': {exc}", exc_info=True)
            doc.status = "FAILED"
            doc.error_message = str(exc)
            await db.commit()
            await db.refresh(doc)
            raise

    @staticmethod
    async def list_documents(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Document], int]:
        """Fetch paginated list of ingested documents."""
        count_stmt = select(func.count(Document.id))
        count_res = await db.execute(count_stmt)
        total = count_res.scalar() or 0

        offset = max(0, (page - 1) * page_size)
        query = (
            select(Document)
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        res = await db.execute(query)
        items = list(res.scalars().all())

        return items, total

    @staticmethod
    async def get_document(
        db: AsyncSession,
        document_id: uuid.UUID,
    ) -> Optional[Document]:
        """Fetch single document metadata with chunks loaded."""
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.chunks))
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def delete_document(
        db: AsyncSession,
        document_id: uuid.UUID,
    ) -> bool:
        """Delete document, its chunks, associated vectors, and stored disk file."""
        doc = await DocumentService.get_document(db, document_id)
        if not doc:
            return False

        # 1. Remove from FAISS index
        vector_store = get_vector_store()
        vector_store.delete_document(str(document_id))

        # 2. Remove physical file from disk
        settings = get_settings()
        file_path = Path(settings.DOCUMENT_STORAGE_PATH) / doc.filename
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError as err:
                logger.warning(f"Could not remove physical file {file_path}: {err}")

        # 3. Delete from DB (cascades to chunks)
        await db.delete(doc)
        await db.commit()

        logger.info(f"Document {document_id} ('{doc.original_filename}') completely deleted.")
        return True

    @staticmethod
    async def rebuild_vector_index(db: AsyncSession) -> Dict[str, Any]:
        """Reconstruct entire FAISS index from completed document chunks in PostgreSQL."""
        logger.info("Rebuilding FAISS vector store from database records...")
        stmt = (
            select(Document)
            .where(Document.status == "COMPLETED")
            .options(selectinload(Document.chunks))
        )
        res = await db.execute(stmt)
        docs = list(res.scalars().all())

        all_vectors: List[List[float]] = []
        all_metadata: List[Dict[str, Any]] = []
        embedding_provider = get_embedding_provider()

        total_chunks = 0
        for doc in docs:
            if not doc.chunks:
                continue
            chunk_texts = [c.content for c in doc.chunks]
            vectors = embedding_provider.embed_documents(chunk_texts)
            all_vectors.extend(vectors)

            for c in doc.chunks:
                all_metadata.append(
                    {
                        "chunk_id": str(c.id),
                        "document_id": str(doc.id),
                        "filename": doc.original_filename,
                        "page_number": c.page_number,
                        "content": c.content,
                    }
                )
                total_chunks += 1

        vector_store = get_vector_store()
        vector_store.rebuild(all_vectors, all_metadata)

        return {
            "documents_processed": len(docs),
            "chunks_processed": total_chunks,
            "vectors_generated": len(all_vectors),
            "final_index_size": vector_store.total_vectors,
        }
