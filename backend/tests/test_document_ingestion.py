"""Tests for document loaders, text splitter, and DocumentService ingestion."""

import pytest
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.documents.chunking.splitter import DocumentSplitter, TextChunk
from backend.app.documents.loaders.text import TextLoader
from backend.app.documents.loaders.markdown import MarkdownLoader
from backend.app.documents.service import DocumentService


def test_text_loader(tmp_path: Path):
    """Verify TextDocumentLoader extracts text content."""
    test_file = tmp_path / "sample.txt"
    test_file.write_text("Hello world, this is a plain text file for testing.", encoding="utf-8")

    loader = TextLoader()
    pages = loader.load(test_file)
    assert len(pages) == 1
    assert "plain text file" in pages[0].text
    assert pages[0].page_number == 1


def test_markdown_loader(tmp_path: Path):
    """Verify MarkdownDocumentLoader extracts markdown headers and body."""
    test_file = tmp_path / "sample.md"
    content = "# Architecture\n\nThis is an architectural overview.\n\n## Components\n- Agent 1\n- Agent 2"
    test_file.write_text(content, encoding="utf-8")

    loader = MarkdownLoader()
    pages = loader.load(test_file)
    assert len(pages) == 1
    assert "Architecture" in pages[0].text
    assert "Components" in pages[0].text


def test_document_splitter():
    """Verify DocumentSplitter splits text into chunks with overlap and page preservation."""
    loader = TextLoader()
    # Mock page with 1000 characters
    sample_text = "Word " * 200
    from backend.app.documents.loaders.base import DocumentPage
    pages = [
        DocumentPage(page_number=1, text=sample_text[:500]),
        DocumentPage(page_number=2, text=sample_text[500:]),
    ]

    splitter = DocumentSplitter(chunk_size=200, chunk_overlap=50)
    chunks = splitter.split_pages(pages)

    assert len(chunks) > 1
    for c in chunks:
        assert isinstance(c, TextChunk)
        assert c.page_number in (1, 2)
        assert len(c.content) > 0


@pytest.mark.asyncio
async def test_document_service_ingest_and_duplicate_detection(db_session: AsyncSession):
    """Verify DocumentService ingests text file and handles duplicates gracefully."""
    sample_bytes = b"PostgreSQL is a powerful, open-source object-relational database system."
    filename = "database_guide.txt"

    # Ingest for the first time
    doc = await DocumentService.ingest_document(
        db=db_session,
        file_bytes=sample_bytes,
        original_filename=filename,
        content_type="text/plain",
    )
    assert doc is not None
    assert doc.status == "COMPLETED"
    assert doc.original_filename == filename
    assert doc.chunk_count > 0

    first_doc_id = doc.id

    # Ingest the exact same content again -> should detect duplicate SHA-256 and return existing doc
    doc2 = await DocumentService.ingest_document(
        db=db_session,
        file_bytes=sample_bytes,
        original_filename="renamed_guide.txt",
        content_type="text/plain",
    )
    assert doc2.id == first_doc_id
    assert doc2.status == "COMPLETED"


@pytest.mark.asyncio
async def test_document_service_empty_file_rejected(db_session: AsyncSession):
    """Verify DocumentService rejects empty files."""
    with pytest.raises(ValueError, match="empty"):
        await DocumentService.ingest_document(
            db=db_session,
            file_bytes=b"",
            original_filename="empty.txt",
        )
