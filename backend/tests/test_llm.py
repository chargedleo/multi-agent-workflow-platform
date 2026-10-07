"""Tests for LLM Abstraction Service and Mock Chat Model."""

import pytest
from backend.app.core.config import Settings
from backend.app.models.schemas import Plan, ResearchResult, WorkflowResponse
from backend.app.services.llm import MockChatModel, get_llm, invoke_structured


@pytest.mark.asyncio
async def test_mock_chat_model_structured_plan():
    """Verify MockChatModel generates valid Plan structured output."""
    mock_llm = MockChatModel()
    structured = mock_llm.with_structured_output(Plan)
    plan: Plan = await structured.ainvoke("Compare PostgreSQL and MongoDB")
    assert isinstance(plan, Plan)
    assert len(plan.goal) > 5
    assert len(plan.steps) >= 2


@pytest.mark.asyncio
async def test_mock_chat_model_structured_research():
    """Verify MockChatModel generates valid ResearchResult structured output."""
    mock_llm = MockChatModel()
    structured = mock_llm.with_structured_output(ResearchResult)
    result: ResearchResult = await structured.ainvoke("Analyze scalability")
    assert isinstance(result, ResearchResult)
    assert len(result.findings) >= 1
    assert len(result.assumptions) >= 1


@pytest.mark.asyncio
async def test_mock_chat_model_structured_workflow_response():
    """Verify MockChatModel generates valid WorkflowResponse structured output."""
    mock_llm = MockChatModel()
    structured = mock_llm.with_structured_output(WorkflowResponse)
    response: WorkflowResponse = await structured.ainvoke("Provide final recommendation")
    assert isinstance(response, WorkflowResponse)
    assert len(response.answer) > 10
    assert len(response.key_points) >= 1
    assert 0.0 <= response.confidence <= 1.0


def test_get_llm_factory_selection():
    """Verify get_llm returns appropriate models based on settings."""
    mock_settings = Settings(LLM_PROVIDER="mock")
    llm = get_llm(settings=mock_settings)
    assert isinstance(llm, MockChatModel)

    openai_settings = Settings(LLM_PROVIDER="openai", LLM_API_KEY="test-key", LLM_MODEL="gpt-4o")
    openai_llm = get_llm(settings=openai_settings)
    assert openai_llm.model_name == "gpt-4o"
