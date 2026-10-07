"""Pydantic schemas and models for the Validation & Guardrails layer."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    """Overall outcome of the validation evaluation."""

    PASS = "PASS"
    FAIL = "FAIL"
    RECOVERABLE = "RECOVERABLE"
    BLOCKED = "BLOCKED"


class ValidationSeverity(str, Enum):
    """Severity level of an individual validation finding."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ValidationCategory(str, Enum):
    """Categorization of validation checks."""

    RESPONSE_SCHEMA = "RESPONSE_SCHEMA"
    CITATION_PROVENANCE = "CITATION_PROVENANCE"
    NUMERICAL_CONSISTENCY = "NUMERICAL_CONSISTENCY"
    TOOL_OUTPUT = "TOOL_OUTPUT"
    CLAIM_VERIFICATION = "CLAIM_VERIFICATION"


class ValidationIssue(BaseModel):
    """A single finding or violation identified by a validator."""

    code: str = Field(..., description="Unique machine-readable identifier for the issue type")
    severity: ValidationSeverity = Field(..., description="Severity level of the issue")
    category: ValidationCategory = Field(..., description="Validation category")
    message: str = Field(..., description="Human-readable description of the issue")
    evidence: Optional[str] = Field(default=None, description="Supporting context or ground truth evidence")
    source: Optional[str] = Field(default=None, description="Origin of the issue (e.g., citation, tool, response)")
    recoverable: bool = Field(default=False, description="Whether the issue can be corrected by re-prompting the agent")


class ValidationResult(BaseModel):
    """Comprehensive result of the validation evaluation for a workflow run."""

    status: ValidationStatus = Field(..., description="Overall validation status: PASS, FAIL, RECOVERABLE, BLOCKED")
    score: float = Field(default=1.0, ge=0.0, le=1.0, description="Calibrated validation score (0.0 to 1.0)")
    issues: List[ValidationIssue] = Field(default_factory=list, description="List of recorded validation issues")
    checked_items: int = Field(default=0, ge=0, description="Total number of verification checks performed")
    failed_items: int = Field(default=0, ge=0, description="Total number of failed checks (errors and warnings)")
    validator_name: str = Field(default="comprehensive_workflow_guardrails", description="Identifier of the validator engine")
    validation_duration_ms: float = Field(default=0.0, ge=0.0, description="Execution duration in milliseconds")
    attempt: int = Field(default=1, ge=1, description="Current validation attempt iteration")
