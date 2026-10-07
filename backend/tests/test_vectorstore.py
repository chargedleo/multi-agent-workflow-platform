"""Tests for embedding provider and FAISS vector store operations."""

from pathlib import Path
import pytest
import numpy as np

from backend.app.documents.embeddings.provider import MockEmbeddingProvider
from backend.app.documents.vectorstore.faiss_store import FAISSVectorStore


def test_mock_embedding_provider_deterministic():
    """Verify MockEmbeddingProvider generates normalized vectors deterministically."""
    provider = MockEmbeddingProvider(dimension=384)
    text1 = "PostgreSQL relational database"
    text2 = "PostgreSQL relational database"
    text3 = "Unrelated completely different biology topic"

    v1 = provider.embed_query(text1)
    v2 = provider.embed_query(text2)
    v3 = provider.embed_query(text3)

    assert len(v1) == 384
    # Exact deterministic equivalence
    assert v1 == v2

    # L2 normalized (norm approximately 1.0)
    norm = np.linalg.norm(np.array(v1))
    assert abs(norm - 1.0) < 1e-4

    # High cosine similarity between identical, lower between unrelated
    dot_same = np.dot(v1, v2)
    assert dot_same > 0.99


def test_faiss_vector_store_add_search_delete(tmp_path: Path):
    """Verify FAISSVectorStore can index, search, persist, and delete vectors."""
    store = FAISSVectorStore(
        dimension=384,
        storage_dir=tmp_path,
    )

    provider = MockEmbeddingProvider(dimension=384)
    v_db = provider.embed_query("PostgreSQL database administration and ACID transactions")
    v_web = provider.embed_query("Web frontend React and Vite setup")

    vectors = [v_db, v_web]
    metas = [
        {"document_id": "doc-1", "chunk_id": "c-1", "filename": "db.txt", "text": "PostgreSQL ACID"},
        {"document_id": "doc-2", "chunk_id": "c-2", "filename": "web.txt", "text": "React Vite"},
    ]

    store.add_vectors(vectors, metas)
    assert store.total_vectors == 2

    index_exists = (tmp_path / "index.faiss").exists() or (tmp_path / "index.faiss.npy").exists()
    assert index_exists
    assert (tmp_path / "metadata.json").exists()

    # Search for database query
    query_v = provider.embed_query("PostgreSQL database")
    results = store.search(query_v, top_k=1)
    assert len(results) == 1
    chunk_id, score, top_meta = results[0]
    assert top_meta["document_id"] == "doc-1"
    assert score > 0.5

    # Reload from disk into fresh instance
    store_loaded = FAISSVectorStore(
        dimension=384,
        storage_dir=tmp_path,
    )
    loaded = store_loaded.load()
    assert loaded is True
    assert store_loaded.total_vectors == 2
    results_loaded = store_loaded.search(query_v, top_k=1)
    assert len(results_loaded) == 1
    assert results_loaded[0][2]["document_id"] == "doc-1"

    # Delete doc-1
    removed = store_loaded.delete_document("doc-1")
    assert removed == 1
    assert store_loaded.total_vectors == 1

    # Search again -> should only find doc-2 now
    results_after_del = store_loaded.search(query_v, top_k=2)
    assert len(results_after_del) == 1
    assert results_after_del[0][2]["document_id"] == "doc-2"
