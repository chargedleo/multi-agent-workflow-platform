"""Shared state definition for LangGraph workflows.

Implements a strongly typed state schema passing data between the Planner,
Research, and Response agents, designed with extension points for future milestones.
"""

from typing import Annotated, Any, Dict, List, Optional
import operator
from typing_extensions import TypedDict


class WorkflowState(TypedDict, total=False):
    """Shared state dictionary representing the workflow pipeline execution."""

    # Core Milestone 1 state attributes
    request_id: str
    user_query: str
    plan: Optional[Dict[str, Any]]
    research_results: Optional[Dict[str, Any]]
    intermediate_results: Annotated[List[Dict[str, Any]], operator.add]
    final_answer: Optional[Dict[str, Any]]
    errors: Annotated[List[str], operator.add]
    metadata: Dict[str, Any]

    # Future Milestone extension slots (Document retrieval, Analysis, Validation, HITL)
    retrieved_documents: Optional[List[Dict[str, Any]]]
    analysis_results: Optional[Dict[str, Any]]
    validation_results: Optional[Dict[str, Any]]
    tool_calls: Optional[List[Dict[str, Any]]]
    approval_status: Optional[str]


def create_initial_state(query: str, request_id: str, metadata: Optional[Dict[str, Any]] = None) -> WorkflowState:
    """Helper to initialize a clean workflow state."""
    return WorkflowState(
        request_id=request_id,
        user_query=query,
        plan=None,
        research_results=None,
        intermediate_results=[],
        final_answer=None,
        errors=[],
        metadata=metadata or {},
        retrieved_documents=None,
        analysis_results=None,
        validation_results=None,
        tool_calls=None,
        approval_status=None,
    )
