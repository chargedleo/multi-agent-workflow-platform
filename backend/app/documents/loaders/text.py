"""Loader for plain text (.txt) files."""

from pathlib import Path
from typing import List

from backend.app.documents.loaders.base import BaseLoader, DocumentPage


class TextLoader(BaseLoader):
    """Extracts text content from plain text files with robust encoding fallbacks."""

    def load(self, file_path: Path) -> List[DocumentPage]:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # Fallback for Windows-1252 or Latin-1 encoded documents
            with open(file_path, "r", encoding="latin-1", errors="replace") as f:
                content = f.read()

        return [DocumentPage(page_number=1, text=content)]
