"""Shared state definition for LangGraph workflows.

Implements a strongly typed state schema passing data between the Planner,
Research, and Response agents, designed with extension points for persistence and future milestones.
"""

from typing import Annotated, Any, Dict, List, Optional
import operator
from typing_extensions import TypedDict


class WorkflowState(TypedDict, total=False):
    """Shared state dictionary representing the workflow pipeline execution."""

    # Core Milestone 1 & 2 state attributes
    request_id: str
    run_id: Optional[str]
    user_query: str
    status: Optional[str]
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
    validation_attempt: Optional[int]
    validation_issues: Optional[List[Dict[str, Any]]]
    validation_history: Optional[List[Dict[str, Any]]]
    # Human-in-the-Loop Approval slots (Milestone 6)
    approval_status: Optional[str]
    approval_required: Optional[bool]
    approval_decision: Optional[str]
    approval_feedback: Optional[str]
    approval_revision: Optional[int]
    approval_history: Optional[List[Dict[str, Any]]]


def create_initial_state(
    query: str,
    request_id: str,
    run_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> WorkflowState:
    """Helper to initialize a clean workflow state with run_id and request_id."""
    return WorkflowState(
        request_id=request_id,
        run_id=run_id,
        user_query=query,
        status="PENDING",
        plan=None,
        research_results=None,
        intermediate_results=[],
        final_answer=None,
        errors=[],
        metadata=metadata or {},
        retrieved_documents=None,
        analysis_results=None,
        validation_results=None,
        validation_attempt=0,
        validation_issues=[],
        validation_history=[],
        tool_calls=None,
        approval_status=None,
        approval_required=True,
        approval_decision=None,
        approval_feedback=None,
        approval_revision=0,
        approval_history=[],
    )
