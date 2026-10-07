"""FAISS Vector Store with disk persistence, deterministic ID mapping, and thread safety."""

import json
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

# Try importing native faiss; otherwise use pure NumPy IndexFlatIP fallback
try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False
    logger.info("Native faiss package not detected. Using optimized NumPy IndexFlatIP fallback.")


class _NumpyIndexFlatIP:
    """NumPy-backed exact Inner Product (cosine similarity on normalized vectors) index."""

    def __init__(self, dimension: int) -> None:
        self.d = dimension
        self.vectors = np.empty((0, dimension), dtype=np.float32)

    @property
    def ntotal(self) -> int:
        return self.vectors.shape[0]

    def add(self, x: np.ndarray) -> None:
        if x.ndim == 1:
            x = x.reshape(1, -1)
        if x.shape[1] != self.d:
            raise ValueError(f"Vector dimension {x.shape[1]} does not match index dimension {self.d}")
        if self.vectors.shape[0] == 0:
            self.vectors = x.astype(np.float32)
        else:
            self.vectors = np.vstack([self.vectors, x.astype(np.float32)])

    def search(self, x: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self.ntotal == 0:
            return np.empty((x.shape[0], 0), dtype=np.float32), np.empty((x.shape[0], 0), dtype=np.int64)

        if x.ndim == 1:
            x = x.reshape(1, -1)

        # Inner product on L2-normalized vectors = cosine similarity
        scores = np.dot(x, self.vectors.T)  # shape (n_queries, ntotal)
        actual_k = min(k, self.ntotal)

        # Sort descending
        indices = np.argsort(-scores, axis=1)[:, :actual_k]
        top_scores = np.take_along_axis(scores, indices, axis=1)

        return top_scores.astype(np.float32), indices.astype(np.int64)

    def reset(self) -> None:
        self.vectors = np.empty((0, self.d), dtype=np.float32)


class FAISSVectorStore:
    """Thread-safe vector store backed by FAISS (or exact NumPy IndexFlatIP).

    Maintains vector ID -> chunk metadata mappings and persists both the
    vector index and metadata to disk.
    """

    def __init__(self, dimension: int, storage_dir: Optional[Path] = None) -> None:
        self.dimension = dimension
        self.storage_dir = storage_dir or Path(get_settings().FAISS_INDEX_PATH)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._lock = Lock()
        self._metadata: List[Dict[str, Any]] = []  # Index i corresponds to vector ID i
        self._index = self._create_empty_index()

    def _create_empty_index(self) -> Any:
        if HAS_FAISS:
            return faiss.IndexFlatIP(self.dimension)
        return _NumpyIndexFlatIP(self.dimension)

    @property
    def total_vectors(self) -> int:
        """Return count of vectors currently indexed."""
        with self._lock:
            return self._index.ntotal

    def add_vectors(
        self,
        vectors: List[List[float]],
        metadata_list: List[Dict[str, Any]],
    ) -> List[int]:
        """Add embedding vectors and associated chunk metadata to index.

        Args:
            vectors: List of float vectors of size self.dimension.
            metadata_list: List of metadata dicts corresponding to each vector.

        Returns:
            List of assigned integer vector IDs.
        """
        if not vectors:
            return []
        if len(vectors) != len(metadata_list):
            raise ValueError("Length of vectors and metadata_list must match")

        with self._lock:
            arr = np.array(vectors, dtype=np.float32)
            # Ensure L2 normalization for inner product = cosine similarity
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            arr = arr / norms

            start_id = self._index.ntotal
            self._index.add(arr)
            self._metadata.extend(metadata_list)

            vector_ids = list(range(start_id, start_id + len(vectors)))
            logger.info(f"Added {len(vectors)} vectors to FAISS index. Total now: {self._index.ntotal}")

            self._save_unlocked()
            return vector_ids

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Perform similarity search for query vector.

        Returns:
            List of tuples: (chunk_id, similarity_score, metadata)
        """
        with self._lock:
            if self._index.ntotal == 0:
                return []

            q_arr = np.array([query_vector], dtype=np.float32)
            q_norm = np.linalg.norm(q_arr)
            if q_norm > 0:
                q_arr = q_arr / q_norm

            scores, indices = self._index.search(q_arr, top_k)

            results: List[Tuple[str, float, Dict[str, Any]]] = []
            row_scores = scores[0]
            row_indices = indices[0]

            for score, idx in zip(row_scores, row_indices):
                if idx < 0 or idx >= len(self._metadata):
                    continue
                meta = self._metadata[idx]
                chunk_id = str(meta.get("chunk_id", ""))
                results.append((chunk_id, float(score), dict(meta)))

            return results

    def delete_document(self, document_id: str) -> int:
        """Remove all vectors belonging to specified document_id and rebuild index.

        Ensures no orphan vectors remain in FAISS.

        Returns:
            Count of deleted vectors.
        """
        with self._lock:
            doc_id_str = str(document_id)
            kept_vectors = []
            kept_meta = []
            deleted_count = 0

            # Reconstruct remaining vectors
            for i, meta in enumerate(self._metadata):
                if str(meta.get("document_id", "")) == doc_id_str:
                    deleted_count += 1
                else:
                    if HAS_FAISS:
                        vec = np.zeros(self.dimension, dtype=np.float32)
                        self._index.reconstruct(i, vec)
                        kept_vectors.append(vec)
                    else:
                        kept_vectors.append(self._index.vectors[i])
                    kept_meta.append(meta)

            if deleted_count > 0:
                self._index = self._create_empty_index()
                self._metadata = kept_meta

                if kept_vectors:
                    arr = np.array(kept_vectors, dtype=np.float32)
                    self._index.add(arr)

                logger.info(f"Deleted {deleted_count} vectors for document '{document_id}'. Remaining: {self._index.ntotal}")
                self._save_unlocked()

            return deleted_count

    def rebuild(
        self,
        vectors: List[List[float]],
        metadata_list: List[Dict[str, Any]],
    ) -> None:
        """Wipe index and reconstruct completely from supplied vectors and metadata."""
        with self._lock:
            self._index = self._create_empty_index()
            self._metadata = []

            if vectors:
                arr = np.array(vectors, dtype=np.float32)
                norms = np.linalg.norm(arr, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                arr = arr / norms
                self._index.add(arr)
                self._metadata = list(metadata_list)

            logger.info(f"Rebuilt FAISS index with {len(vectors)} vectors.")
            self._save_unlocked()

    def save(self) -> None:
        """Public thread-safe save."""
        with self._lock:
            self._save_unlocked()

    def _save_unlocked(self) -> None:
        """Save index and metadata to disk."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        index_file = self.storage_dir / "index.faiss"
        meta_file = self.storage_dir / "metadata.json"

        if HAS_FAISS:
            faiss.write_index(self._index, str(index_file))
        else:
            # Save numpy array representation
            np.save(str(index_file), self._index.vectors)

        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "dimension": self.dimension,
                    "total_vectors": self._index.ntotal,
                    "metadata": self._metadata,
                },
                f,
                indent=2,
            )

    def load(self) -> bool:
        """Load index and metadata from disk if available.

        Returns:
            True if loaded successfully, False if index files do not exist yet.
        """
        with self._lock:
            index_file = self.storage_dir / "index.faiss"
            # Support both index.faiss and index.faiss.npy fallback
            npy_index_file = self.storage_dir / "index.faiss.npy"
            meta_file = self.storage_dir / "metadata.json"

            if not (index_file.exists() or npy_index_file.exists()) or not meta_file.exists():
                logger.info(f"No existing FAISS index found at {self.storage_dir}. Initialized clean index.")
                return False

            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                    self._metadata = meta_data.get("metadata", [])

                if HAS_FAISS and index_file.exists():
                    self._index = faiss.read_index(str(index_file))
                elif HAS_FAISS and npy_index_file.exists():
                    vectors = np.load(str(npy_index_file))
                    self._index = faiss.IndexFlatIP(self.dimension)
                    if vectors.shape[0] > 0:
                        self._index.add(vectors.astype(np.float32))
                elif npy_index_file.exists():
                    vectors = np.load(str(npy_index_file))
                    self._index = _NumpyIndexFlatIP(self.dimension)
                    if vectors.shape[0] > 0:
                        self._index.add(vectors)
                elif index_file.exists():
                    try:
                        vectors = np.load(str(index_file))
                        self._index = _NumpyIndexFlatIP(self.dimension)
                        if vectors.shape[0] > 0:
                            self._index.add(vectors)
                    except Exception:
                        self._index = self._create_empty_index()

                logger.info(f"Loaded FAISS index from {self.storage_dir} with {self._index.ntotal} vectors.")
                return True
            except Exception as exc:
                logger.error(f"Failed to load FAISS index from {self.storage_dir}: {exc}. Reinitializing empty.")
                self._index = self._create_empty_index()
                self._metadata = []
                return False


_vector_store_instance: Optional[FAISSVectorStore] = None


def get_vector_store() -> FAISSVectorStore:
    """Return process-singleton FAISS vector store."""
    global _vector_store_instance
    if _vector_store_instance is None:
        settings = get_settings()
        _vector_store_instance = FAISSVectorStore(
            dimension=settings.EMBEDDING_DIMENSION,
            storage_dir=Path(settings.FAISS_INDEX_PATH),
        )
        _vector_store_instance.load()
    return _vector_store_instance


def reset_vector_store() -> None:
    """Reset vector store singleton instance (useful for unit testing)."""
    global _vector_store_instance
    _vector_store_instance = None
