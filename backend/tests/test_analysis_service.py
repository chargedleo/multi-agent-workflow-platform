"""Unit tests for DataAnalysisService and safe analytical operations."""

import pytest
from backend.app.analysis.schemas import (
    AnalysisOperation,
    AnalysisRequest,
    FilterCondition,
    FilterOperator,
    SortOrder,
)
from backend.app.analysis.service import DataAnalysisService


def test_get_dataset_schema():
    schema = DataAnalysisService.get_schema("orders")
    assert schema.dataset_name == "orders"
    assert schema.row_count == 20
    col_names = [c.name for c in schema.columns]
    assert "revenue" in col_names
    assert "region" in col_names
    assert "quantity" in col_names


def test_count_operation():
    req = AnalysisRequest(
        dataset="orders",
        operation=AnalysisOperation.COUNT,
    )
    result = DataAnalysisService.analyze(req)
    assert result.success is True
    assert result.metrics["count"] == 20
    assert result.metrics["record_count"] == 20


def test_sum_revenue_operation():
    req = AnalysisRequest(
        dataset="orders",
        operation=AnalysisOperation.SUM,
        columns=["revenue"],
    )
    result = DataAnalysisService.analyze(req)
    assert result.success is True
    assert result.metrics["sum_revenue"] == 177650.0


def test_mean_operation():
    req = AnalysisRequest(
        dataset="orders",
        operation=AnalysisOperation.MEAN,
        columns=["revenue"],
    )
    result = DataAnalysisService.analyze(req)
    assert result.success is True
    assert result.metrics["mean_revenue"] == 8882.5


def test_min_and_max_operation():
    min_req = AnalysisRequest(
        dataset="orders",
        operation=AnalysisOperation.MIN,
        columns=["quantity"],
    )
    min_res = DataAnalysisService.analyze(min_req)
    assert min_res.success is True
    assert min_res.metrics["min_quantity"] == 2.0

    max_req = AnalysisRequest(
        dataset="orders",
        operation=AnalysisOperation.MAX,
        columns=["quantity"],
    )
    max_res = DataAnalysisService.analyze(max_req)
    assert max_res.success is True
    assert max_res.metrics["max_quantity"] == 25.0


def test_group_by_region_revenue():
    req = AnalysisRequest(
        dataset="orders",
        operation=AnalysisOperation.GROUP_BY,
        columns=["revenue"],
        group_by=["region"],
    )
    result = DataAnalysisService.analyze(req)
    assert result.success is True
    assert result.metrics["groups_count"] == 4
    # Check that region groups exist
    regions = [r["region"] for r in result.rows]
    assert "North" in regions
    assert "West" in regions
    assert "South" in regions
    assert "East" in regions
    assert result.metrics["total_revenue_sum"] == 177650.0


def test_filter_and_count():
    req = AnalysisRequest(
        dataset="orders",
        operation=AnalysisOperation.COUNT,
        filters=[
            FilterCondition(column="region", operator=FilterOperator.EQ, value="West")
        ],
    )
    result = DataAnalysisService.analyze(req)
    assert result.success is True
    assert result.metrics["count"] == 6


def test_sort_and_top_n():
    req = AnalysisRequest(
        dataset="orders",
        operation=AnalysisOperation.TOP_N,
        columns=["revenue"],
        sort_by="revenue",
        sort_order=SortOrder.DESC,
        limit=5,
    )
    result = DataAnalysisService.analyze(req)
    assert result.success is True
    assert len(result.rows) == 5
    # Highest revenue order is ORD-1008 (Hooli: 22500.0)
    assert result.rows[0]["order_id"] == "ORD-1008"
    assert result.rows[0]["revenue"] == 22500.0


def test_descriptive_stats():
    req = AnalysisRequest(
        dataset="orders",
        operation=AnalysisOperation.DESCRIPTIVE_STATS,
        columns=["revenue"],
    )
    result = DataAnalysisService.analyze(req)
    assert result.success is True
    assert result.metrics["count"] == 20
    assert result.metrics["mean"] == 8882.5
    assert result.metrics["min"] == 4250.0
    assert result.metrics["max"] == 22500.0


def test_invalid_column_rejected():
    req = AnalysisRequest(
        dataset="orders",
        operation=AnalysisOperation.SUM,
        columns=["non_existent_column"],
    )
    result = DataAnalysisService.analyze(req)
    assert result.success is False
    assert len(result.errors) > 0
    assert "does not exist" in result.errors[0]


def test_unapproved_dataset_rejected():
    req = AnalysisRequest(
        dataset="credit_cards_and_secrets",
        operation=AnalysisOperation.COUNT,
    )
    result = DataAnalysisService.analyze(req)
    assert result.success is False
    assert "not in approved allowlist" in result.errors[0]


def test_filter_yielding_empty_dataset():
    req = AnalysisRequest(
        dataset="orders",
        operation=AnalysisOperation.SUM,
        columns=["revenue"],
        filters=[
            FilterCondition(column="region", operator=FilterOperator.EQ, value="Antarctica")
        ],
    )
    result = DataAnalysisService.analyze(req)
    assert result.success is True
    assert result.metrics["sum_revenue"] == 0.0
    assert len(result.warnings) > 0
