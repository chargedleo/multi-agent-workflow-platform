"""Tests for LangGraph multi-agent workflow orchestration."""

import pytest
from backend.app.graph.workflow import run_workflow, build_workflow_graph
from backend.app.graph.state import create_initial_state


@pytest.mark.asyncio
async def test_workflow_execution_end_to_end():
    """Verify that Planner -> Researcher -> Responder executes and populates state."""
    query = "Compare PostgreSQL and MongoDB for a startup SaaS application."
    custom_req_id = "test-req-uuid-12345"

    state = await run_workflow(query=query, request_id=custom_req_id)

    # 1. Verify Request ID propagation
    assert state["request_id"] == custom_req_id
    assert state["user_query"] == query

    # 2. Verify Planner Agent execution
    plan = state.get("plan")
    assert plan is not None
    assert "goal" in plan
    assert "steps" in plan
    assert len(plan["steps"]) >= 2

    # 3. Verify Researcher Agent execution
    research = state.get("research_results")
    assert research is not None
    assert "findings" in research
    assert "assumptions" in research
    assert "unanswered_questions" in research
    assert len(research["findings"]) >= 1

    # 4. Verify Responder Agent execution & Structured Final Output
    final_answer = state.get("final_answer")
    assert final_answer is not None
    assert final_answer["request_id"] == custom_req_id
    assert len(final_answer["answer"]) > 10
    assert len(final_answer["key_points"]) >= 1
    assert 0.0 <= final_answer["confidence"] <= 1.0

    # 5. Verify intermediate results captured from all 3 agents
    intermediate = state.get("intermediate_results", [])
    agents_executed = [step["agent"] for step in intermediate if "agent" in step]
    assert "planner" in agents_executed
    assert "researcher" in agents_executed
    assert "responder" in agents_executed

    # 6. Verify zero fatal errors
    assert len(state.get("errors", [])) == 0


@pytest.mark.asyncio
async def test_workflow_error_capture(monkeypatch):
    """Verify that if an agent encounters an error, it is recorded in state without crashing."""
    import backend.app.graph.workflow as workflow_module

    async def broken_research_agent(state):
        return {
            "errors": ["Simulated research failure: connection timed out"],
            "intermediate_results": [{"agent": "researcher", "error": "Simulated failure"}],
        }

    monkeypatch.setattr(workflow_module, "research_agent", broken_research_agent)

    # Rebuild graph to pick up monkeypatched agent
    test_graph = build_workflow_graph()
    initial_state = create_initial_state(query="Test query", request_id="error-req-999")
    final_state = await test_graph.ainvoke(initial_state)

    assert "errors" in final_state
    assert any("Simulated research failure" in err for err in final_state["errors"])
