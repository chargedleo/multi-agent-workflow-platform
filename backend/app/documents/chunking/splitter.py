"""Deterministic text chunking and document splitting."""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.app.documents.loaders.base import DocumentPage


@dataclass
class TextChunk:
    """Represents a text segment extracted from a document page."""

    chunk_index: int
    content: str
    page_number: int
    start_char: int
    end_char: int
    token_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentSplitter:
    """Recursively splits document text into overlapping chunks while preserving page provenance."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
        separators: Optional[List[str]] = None,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be non-negative and less than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", "? ", "! ", "; ", " ", ""]

    def _split_text(self, text: str) -> List[str]:
        """Split text into pieces smaller than chunk_size using recursive separators."""
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        # Find the best separator
        for sep in self.separators:
            if sep == "":
                # Character level fallback
                step = self.chunk_size - self.chunk_overlap
                return [text[i : i + self.chunk_size] for i in range(0, len(text), step) if text[i : i + self.chunk_size].strip()]

            splits = text.split(sep)
            if len(splits) > 1:
                pieces: List[str] = []
                current_piece = ""

                for part in splits:
                    candidate = f"{current_piece}{sep}{part}" if current_piece else part
                    if len(candidate) <= self.chunk_size:
                        current_piece = candidate
                    else:
                        if current_piece.strip():
                            pieces.append(current_piece.strip())
                        # If a single part is larger than chunk_size, recursively split it
                        if len(part) > self.chunk_size:
                            sub_pieces = self._split_text(part)
                            pieces.extend(sub_pieces)
                            current_piece = ""
                        else:
                            current_piece = part

                if current_piece.strip():
                    pieces.append(current_piece.strip())

                if pieces:
                    # Apply overlap across contiguous pieces if needed
                    return self._merge_with_overlap(pieces)

        return [text]

    def _merge_with_overlap(self, pieces: List[str]) -> List[str]:
        """Combine pieces up to chunk_size and maintain chunk_overlap."""
        merged: List[str] = []
        current = ""

        for piece in pieces:
            if not current:
                current = piece
            elif len(current) + 1 + len(piece) <= self.chunk_size:
                current = f"{current} {piece}"
            else:
                merged.append(current)
                # Keep tail of current for overlap
                overlap_text = current[-self.chunk_overlap :] if len(current) > self.chunk_overlap else current
                current = f"{overlap_text} {piece}".strip()

        if current.strip():
            merged.append(current.strip())

        return merged

    def split_pages(self, pages: List[DocumentPage]) -> List[TextChunk]:
        """Split a sequence of pages into numbered TextChunk instances."""
        chunks: List[TextChunk] = []
        global_chunk_idx = 0

        for page in pages:
            raw_text = page.text.strip()
            if not raw_text:
                continue

            page_segments = self._split_text(raw_text)
            char_cursor = 0

            for segment in page_segments:
                seg_text = segment.strip()
                if not seg_text:
                    continue

                start_idx = raw_text.find(seg_text[:min(20, len(seg_text))], char_cursor)
                if start_idx == -1:
                    start_idx = char_cursor
                end_idx = start_idx + len(seg_text)
                char_cursor = max(char_cursor, start_idx + 1)

                # Estimate token count (~4 characters per token)
                token_count = max(1, len(seg_text) // 4)

                chunks.append(
                    TextChunk(
                        chunk_index=global_chunk_idx,
                        content=seg_text,
                        page_number=page.page_number,
                        start_char=start_idx,
                        end_char=end_idx,
                        token_count=token_count,
                        metadata=dict(page.metadata),
                    )
                )
                global_chunk_idx += 1

        return chunks
