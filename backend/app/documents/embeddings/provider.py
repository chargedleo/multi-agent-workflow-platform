"""Centralized embedding provider abstraction."""

from abc import ABC, abstractmethod
import hashlib
import re
from typing import List, Optional
import numpy as np

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding generation."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of embedding vectors."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding vector for a single query."""
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a batch of document texts."""
        pass


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic token-hash & character n-gram embedding generator.

    Generates L2-normalized vectors of fixed dimension. Texts sharing terms
    and semantic stems produce higher cosine similarity without requiring external APIs.
    """

    def __init__(self, dimension: int = 384) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _embed_single(self, text: str) -> List[float]:
        if not text:
            vec = np.zeros(self._dimension, dtype=np.float32)
            vec[0] = 1.0
            return vec.tolist()

        vec = np.zeros(self._dimension, dtype=np.float32)
        tokens = re.findall(r"\w+", text.lower())

        for token in tokens:
            # Word-level hash features
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            idx1 = h % self._dimension
            idx2 = (h >> 32) % self._dimension
            weight = 1.0 / (1.0 + np.log(1.0 + len(token)))
            vec[idx1] += weight
            vec[idx2] += weight * 0.5

            # 3-gram character features for subword similarity
            if len(token) >= 3:
                for i in range(len(token) - 2):
                    ngram = token[i : i + 3]
                    h_ng = int(hashlib.md5(ngram.encode("utf-8")).hexdigest(), 16)
                    ng_idx = h_ng % self._dimension
                    vec[ng_idx] += 0.25

        # L2 normalization for cosine similarity
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        else:
            vec[0] = 1.0

        return vec.tolist()

    def embed_query(self, text: str) -> List[float]:
        return self._embed_single(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_single(t) for t in texts]


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding generator using fastembed or sentence-transformers."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model = None
        self._dim = 384
        self._init_model()

    def _init_model(self) -> None:
        try:
            from fastembed import TextEmbedding
            logger.info(f"Loading FastEmbed model '{self.model_name}'...")
            self._model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            self._dim = 384
            return
        except Exception:
            pass

        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading SentenceTransformer model '{self.model_name}'...")
            self._model = SentenceTransformer(self.model_name)
            self._dim = self._model.get_sentence_embedding_dimension()
            return
        except Exception:
            pass

        logger.warning(
            "Neither fastembed nor sentence-transformers is available. Falling back to MockEmbeddingProvider."
        )
        self._fallback = MockEmbeddingProvider(dimension=384)

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_query(self, text: str) -> List[float]:
        if hasattr(self, "_fallback"):
            return self._fallback.embed_query(text)
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if hasattr(self, "_fallback"):
            return self._fallback.embed_documents(texts)

        if hasattr(self._model, "embed"):  # fastembed
            embeddings = list(self._model.embed(texts))
            return [e.tolist() for e in embeddings]
        else:  # sentence-transformers
            embeddings = self._model.encode(texts, normalize_embeddings=True)
            return embeddings.tolist()


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI or OpenAI-compatible embedding API."""

    def __init__(self, model: str = "text-embedding-3-small", api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self._dim = 1536

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        res = client.embeddings.create(input=texts, model=self.model)
        return [item.embedding for item in res.data]


_embedding_provider_instance: Optional[EmbeddingProvider] = None


def get_embedding_provider() -> EmbeddingProvider:
    """Return process-singleton embedding provider configured via settings."""
    global _embedding_provider_instance
    if _embedding_provider_instance is None:
        settings = get_settings()
        provider_type = settings.EMBEDDING_PROVIDER.lower().strip()

        if provider_type == "mock":
            _embedding_provider_instance = MockEmbeddingProvider(
                dimension=settings.EMBEDDING_DIMENSION
            )
        elif provider_type == "local":
            _embedding_provider_instance = LocalEmbeddingProvider(
                model_name=settings.EMBEDDING_MODEL
            )
        elif provider_type == "openai":
            _embedding_provider_instance = OpenAIEmbeddingProvider(
                model=settings.EMBEDDING_MODEL,
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
            )
        else:
            logger.warning(
                f"Unknown EMBEDDING_PROVIDER '{provider_type}', using MockEmbeddingProvider."
            )
            _embedding_provider_instance = MockEmbeddingProvider(
                dimension=settings.EMBEDDING_DIMENSION
            )

    return _embedding_provider_instance


def reset_embedding_provider() -> None:
    """Reset singleton instance (useful for unit testing)."""
    global _embedding_provider_instance
    _embedding_provider_instance = None
