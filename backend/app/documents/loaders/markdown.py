"""Loader for Markdown (.md) documents."""

from pathlib import Path
from typing import List

from backend.app.documents.loaders.base import BaseLoader, DocumentPage


class MarkdownLoader(BaseLoader):
    """Extracts content from Markdown documents."""

    def load(self, file_path: Path) -> List[DocumentPage]:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1", errors="replace") as f:
                content = f.read()

        return [DocumentPage(page_number=1, text=content)]
