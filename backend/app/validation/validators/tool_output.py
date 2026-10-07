"""Tool output and invocation validator.

Validates that all external and MCP tool invocations conform to approved tool schemas,
use registered tool names, and that errors are accurately propagated rather than
masked as successes.
"""

from typing import Any, Dict, List, Tuple
from backend.app.validation.schemas import (
    ValidationCategory,
    ValidationIssue,
    ValidationSeverity,
)

APPROVED_TOOL_NAMES = {"analyze_dataset", "get_dataset_schema", "query_postgres"}


def validate_tool_outputs(
    intermediate_results: List[Dict[str, Any]],
    state: Dict[str, Any],
) -> Tuple[List[ValidationIssue], int]:
    """Validate tool outputs across intermediate results.

    Returns:
        Tuple of (recorded_issues, checked_count)
    """
    issues: List[ValidationIssue] = []
    checks = 0

    if not intermediate_results:
        return issues, checks

    for step in intermediate_results:
        if not isinstance(step, dict):
            continue

        agent = step.get("agent")
        if agent != "data_analysis":
            continue

        output = step.get("output") or {}
        if not isinstance(output, dict):
            continue

        # Check if analysis was required
        if not output.get("analysis_required"):
            continue

        checks += 1
        tool_name = output.get("tool_name")
        if not tool_name or tool_name not in APPROVED_TOOL_NAMES:
            issues.append(
                ValidationIssue(
                    code="UNAPPROVED_TOOL_NAME",
                    severity=ValidationSeverity.CRITICAL,
                    category=ValidationCategory.TOOL_OUTPUT,
                    message=f"Tool invocation used unapproved or missing tool name '{tool_name}'.",
                    evidence=f"tool_name={tool_name}, approved={list(APPROVED_TOOL_NAMES)}",
                    recoverable=False,
                    source="tool",
                )
            )

        # Check tool execution success flag vs error
        checks += 1
        tool_success = output.get("tool_success")
        tool_error = output.get("tool_error")

        if tool_success is True and tool_error:
            issues.append(
                ValidationIssue(
                    code="MASKED_TOOL_ERROR",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.TOOL_OUTPUT,
                    message=f"Tool '{tool_name}' reported success=True but contained error message: {tool_error}",
                    evidence=f"tool_error={tool_error}",
                    recoverable=False,
                    source="tool",
                )
            )

        # Check tool arguments structure
        checks += 1
        tool_args = output.get("tool_arguments")
        if tool_args is not None and not isinstance(tool_args, dict):
            issues.append(
                ValidationIssue(
                    code="MALFORMED_TOOL_ARGUMENTS",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.TOOL_OUTPUT,
                    message=f"Tool arguments for '{tool_name}' must be a dictionary object.",
                    evidence=f"type={type(tool_args).__name__}",
                    recoverable=True,
                    source="tool",
                )
            )

    return issues, checks
