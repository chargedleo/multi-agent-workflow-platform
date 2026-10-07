"""Document loaders package."""

from pathlib import Path
from typing import Dict, Type

from backend.app.documents.loaders.base import BaseLoader, DocumentPage
from backend.app.documents.loaders.markdown import MarkdownLoader
from backend.app.documents.loaders.pdf import PDFLoader
from backend.app.documents.loaders.text import TextLoader

_LOADER_MAPPING: Dict[str, Type[BaseLoader]] = {
    ".pdf": PDFLoader,
    ".txt": TextLoader,
    ".md": MarkdownLoader,
    ".markdown": MarkdownLoader,
}


def get_document_loader(filename_or_path: str) -> BaseLoader:
    """Return an appropriate loader based on file extension.

    Raises:
        ValueError: If file format is not supported.
    """
    ext = Path(filename_or_path).suffix.lower()
    loader_cls = _LOADER_MAPPING.get(ext)
    if not loader_cls:
        supported = ", ".join(sorted(_LOADER_MAPPING.keys()))
        raise ValueError(
            f"Unsupported file format '{ext}'. Supported formats: {supported}"
        )
    return loader_cls()


__all__ = [
    "BaseLoader",
    "DocumentPage",
    "PDFLoader",
    "TextLoader",
    "MarkdownLoader",
    "get_document_loader",
]
