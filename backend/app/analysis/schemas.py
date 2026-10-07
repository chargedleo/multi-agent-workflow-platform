"""Pydantic models and schemas for structured data analysis and MCP tool interaction."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class AnalysisOperation(str, Enum):
    """Supported safe analytical operations."""

    COUNT = "count"
    SUM = "sum"
    MEAN = "mean"
    MIN = "min"
    MAX = "max"
    GROUP_BY = "group_by"
    FILTER = "filter"
    SORT = "sort"
    TOP_N = "top_n"
    DESCRIPTIVE_STATS = "descriptive_stats"


class FilterOperator(str, Enum):
    """Allowed comparison operators for filtering."""

    EQ = "=="
    NEQ = "!="
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    IN = "in"
    CONTAINS = "contains"


class SortOrder(str, Enum):
    """Sort direction."""

    ASC = "asc"
    DESC = "desc"


class FilterCondition(BaseModel):
    """A safe, parameterized filter predicate."""

    column: str = Field(..., description="Column to filter by")
    operator: FilterOperator = Field(default=FilterOperator.EQ, description="Comparison operator")
    value: Union[str, int, float, List[Union[str, int, float]]] = Field(..., description="Comparison value")


class AnalysisColumn(BaseModel):
    """Schema descriptor for a dataset column."""

    name: str = Field(..., description="Column name")
    data_type: str = Field(..., description="Data type: string, integer, float, date")


class AnalysisRow(BaseModel):
    """A single record/row in the analysis result."""

    data: Dict[str, Any] = Field(..., description="Key-value mapping of column values")


class AnalysisSummary(BaseModel):
    """Textual and metric summary of the analysis execution."""

    text: str = Field(..., description="Concise human-readable finding from the analysis")
    total_records: int = Field(..., description="Number of records analyzed or returned")
    key_metrics: Dict[str, Any] = Field(default_factory=dict, description="Numerical aggregates computed")


class AnalysisRequest(BaseModel):
    """Structured request specification for analyzing a dataset."""

    dataset: str = Field(..., description="Identifier of the target dataset (e.g., 'orders')")
    operation: AnalysisOperation = Field(..., description="Primary analytical operation")
    columns: Optional[List[str]] = Field(default=None, description="Target column(s) for the operation")
    group_by: Optional[List[str]] = Field(default=None, description="Columns to group by")
    filters: Optional[List[FilterCondition]] = Field(default=None, description="Filter conditions to apply")
    sort_by: Optional[str] = Field(default=None, description="Column to sort results by")
    sort_order: SortOrder = Field(default=SortOrder.ASC, description="Sort direction")
    limit: Optional[int] = Field(default=None, ge=1, le=1000, description="Maximum number of rows to return")


class AnalysisResult(BaseModel):
    """Comprehensive, structured result produced by the DataAnalysisService."""

    success: bool = Field(..., description="Whether the analysis succeeded")
    operation: str = Field(..., description="The operation executed")
    dataset: str = Field(..., description="Dataset analyzed")
    summary: str = Field(..., description="Executive analytical summary")
    columns: List[str] = Field(default_factory=list, description="Output columns present in rows")
    rows: List[Dict[str, Any]] = Field(default_factory=list, description="Output data records")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Aggregated key metrics")
    tool_name: str = Field(default="analyze_dataset", description="Tool used to perform the analysis")
    execution_time_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings")
    errors: List[str] = Field(default_factory=list, description="Error messages if execution failed")


class DatasetSchemaInfo(BaseModel):
    """Metadata schema of an approved dataset."""

    dataset_name: str = Field(..., description="Dataset name")
    description: str = Field(..., description="Description of the dataset contents")
    columns: List[AnalysisColumn] = Field(..., description="Available columns")
    row_count: int = Field(..., description="Total row count in dataset")


class ToolCall(BaseModel):
    """Represents a tool call invoked by an agent."""

    tool_name: str = Field(..., description="Name of the invoked tool")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to the tool")


class ToolResult(BaseModel):
    """Represents the execution result of an agent tool call."""

    tool_name: str = Field(..., description="Name of the executed tool")
    success: bool = Field(..., description="Whether the tool execution succeeded")
    result: Dict[str, Any] = Field(default_factory=dict, description="Structured tool output")
    error: Optional[str] = Field(default=None, description="Error description if tool call failed")
    duration_ms: float = Field(default=0.0, description="Tool execution duration in milliseconds")


class PostgresQueryRequest(BaseModel):
    """Safe, structured query request for PostgreSQL analytical tables."""

    table: str = Field(default="analytics_orders", description="Target approved table name")
    columns: Optional[List[str]] = Field(default=None, description="Columns to project")
    filters: Optional[List[FilterCondition]] = Field(default=None, description="Filter conditions")
    group_by: Optional[List[str]] = Field(default=None, description="Columns to group by")
    aggregations: Optional[Dict[str, str]] = Field(
        default=None,
        description="Aggregations: mapping of column to agg function ('count', 'sum', 'avg', 'min', 'max')",
    )
    order_by: Optional[str] = Field(default=None, description="Column to order by")
    sort_order: SortOrder = Field(default=SortOrder.ASC, description="Order direction")
    limit: Optional[int] = Field(default=100, ge=1, le=1000, description="Max rows")
