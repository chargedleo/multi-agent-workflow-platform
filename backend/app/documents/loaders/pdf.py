"""Loader for PDF documents using PyMuPDF."""

from pathlib import Path
from typing import List

from backend.app.documents.loaders.base import BaseLoader, DocumentPage


class PDFLoader(BaseLoader):
    """Extracts text page-by-page from PDF files using PyMuPDF."""

    def load(self, file_path: Path) -> List[DocumentPage]:
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        try:
            import fitz  # PyMuPDF
        except ImportError:
            try:
                import pymupdf as fitz
            except ImportError:
                raise RuntimeError("PyMuPDF is required for PDF ingestion. Please install pymupdf.")

        try:
            doc = fitz.open(str(file_path))
        except Exception as exc:
            raise ValueError(f"Corrupted or invalid PDF file: {exc}") from exc

        if doc.is_encrypted:
            doc.close()
            raise ValueError("Encrypted or password-protected PDFs are not supported.")

        pages: List[DocumentPage] = []
        try:
            for page_idx in range(len(doc)):
                page = doc.load_page(page_idx)
                text = page.get_text("text") or ""
                pages.append(DocumentPage(page_number=page_idx + 1, text=text))
        finally:
            doc.close()

        if not pages:
            # Empty PDF document
            pages.append(DocumentPage(page_number=1, text=""))

        return pages
