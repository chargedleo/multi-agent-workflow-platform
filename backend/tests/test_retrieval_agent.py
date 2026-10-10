"""Tests for Document Retrieval Agent and LangGraph integration."""

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.document_retrieval import document_retrieval_agent
from backend.app.documents.service import DocumentService
from backend.app.graph.state import create_initial_state
from backend.app.graph.workflow import run_workflow


@pytest.mark.asyncio
async def test_document_retrieval_agent_empty_store():
    """Verify document retrieval agent does not fail when vector store is empty."""
    state = create_initial_state(
        query="What is PostgreSQL?",
        request_id="test-req-empty",
    )
    result = await document_retrieval_agent(state)
    assert "retrieved_documents" in result
    assert isinstance(result["retrieved_documents"], list)
    assert len(result.get("errors", [])) == 0


@pytest.mark.asyncio
async def test_document_retrieval_with_indexed_content(db_session: AsyncSession):
    """Verify retrieval agent finds matching chunks and downstream flow has citations."""
    sample_content = (
        "Antigravity Enterprise Architecture Specification.\n\n"
        "Section 1: The system uses LangGraph for coordinating Planner, Retrieval, Researcher, and Responder agents.\n"
        "Section 2: High throughput messaging is managed via durable PostgreSQL state persistence."
    ).encode("utf-8")
    # Ingest test document
    doc = await DocumentService.ingest_document(
        db=db_session,
        file_bytes=sample_content,
        original_filename="enterprise_arch.txt",
        content_type="text/plain",
    )
    assert doc.status == "COMPLETED"

    # Run workflow querying this specific topic
    query = "Explain the system architecture and how LangGraph coordinates agents."
    final_state = await run_workflow(query=query)

    assert final_state["status"] == "COMPLETED"
    retrieved_docs = final_state.get("retrieved_documents", [])
    assert len(retrieved_docs) > 0

    final_answer = final_state.get("final_answer", {})
    sources = final_answer.get("sources", [])
    assert len(sources) > 0
    assert any("enterprise_arch.txt" in s.get("filename", "") for s in sources)
