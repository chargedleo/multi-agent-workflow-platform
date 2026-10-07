"""Base classes for document loaders."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class DocumentPage:
    """Represents text extracted from a distinct page or section of a document."""

    page_number: int
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseLoader(ABC):
    """Abstract interface for extracting text content from physical files."""

    @abstractmethod
    def load(self, file_path: Path) -> List[DocumentPage]:
        """Extract pages of text from the target file path."""
        pass
