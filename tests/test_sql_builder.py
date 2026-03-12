import pytest

from semantic_query_agent.models import QueryPlan
from semantic_query_agent.sql_builder import build_sql


def test_simple_metric_by_dimension(semantic_model):
    plan = QueryPlan(
        metrics=["total_revenue"],
        dimensions=["region"],
    )
    sql = build_sql(plan, semantic_model)
    assert "SUM(sale_price_eur)" in sql
    assert "region" in sql
    assert "FROM TRANSACTIONS" in sql
    assert "GROUP BY" in sql


def test_metric_with_filter(semantic_model):
    plan = QueryPlan(
        metrics=["units_sold"],
        dimensions=["dealer_name"],
        filters={"vehicle_type": "Electric"},
    )
    sql = build_sql(plan, semantic_model)
    assert "COUNT(transaction_id)" in sql
    assert "dealer_name" in sql
    assert "vehicle_type = 'Electric'" in sql


def test_metric_with_time_period(semantic_model):
    plan = QueryPlan(
        metrics=["avg_deal_margin"],
        dimensions=["region"],
        time_period="last_quarter",
    )
    sql = build_sql(plan, semantic_model)
    assert "AVG((sale_price_eur - cost_eur) / sale_price_eur * 100)" in sql
    assert "sale_date" in sql
    assert "GROUP BY" in sql


def test_metric_only_no_dimensions(semantic_model):
    plan = QueryPlan(
        metrics=["total_revenue"],
    )
    sql = build_sql(plan, semantic_model)
    assert "SUM(sale_price_eur)" in sql
    assert "GROUP BY" not in sql


def test_multiple_metrics(semantic_model):
    plan = QueryPlan(
        metrics=["total_revenue", "units_sold"],
        dimensions=["region"],
    )
    sql = build_sql(plan, semantic_model)
    assert "SUM(sale_price_eur)" in sql
    assert "COUNT(transaction_id)" in sql
    assert "GROUP BY" in sql


def test_sale_month_dimension_translates_to_strftime(semantic_model):
    plan = QueryPlan(
        metrics=["total_revenue"],
        dimensions=["sale_month"],
    )
    sql = build_sql(plan, semantic_model)
    assert "STRFTIME" in sql
    assert "TO_CHAR" not in sql


def test_sale_quarter_dimension_translates_to_strftime(semantic_model):
    plan = QueryPlan(
        metrics=["total_revenue"],
        dimensions=["sale_quarter"],
    )
    sql = build_sql(plan, semantic_model)
    assert "STRFTIME" in sql
    assert "TO_CHAR" not in sql


def test_unknown_metric_raises(semantic_model):
    plan = QueryPlan(metrics=["nonexistent_metric"])
    with pytest.raises(ValueError, match="Unknown metric"):
        build_sql(plan, semantic_model)


def test_unknown_dimension_raises(semantic_model):
    plan = QueryPlan(metrics=["total_revenue"], dimensions=["nonexistent_dim"])
    with pytest.raises(ValueError, match="Unknown dimension"):
        build_sql(plan, semantic_model)


def test_unknown_time_period_raises(semantic_model):
    plan = QueryPlan(metrics=["total_revenue"], time_period="nonexistent_period")
    with pytest.raises(ValueError, match="Unknown time period"):
        build_sql(plan, semantic_model)


def test_sql_executes_revenue_by_region(semantic_model, db_conn):
    plan = QueryPlan(
        metrics=["total_revenue"],
        dimensions=["region"],
        time_period="ytd",
    )
    sql = build_sql(plan, semantic_model)
    result = db_conn.execute(sql).fetchall()
    assert len(result) > 0
    # Each row should have (region, total_revenue)
    for row in result:
        assert isinstance(row[0], str)  # region
        assert row[1] > 0  # revenue > 0


def test_sql_executes_electric_vehicles_by_dealer(semantic_model, db_conn):
    plan = QueryPlan(
        metrics=["units_sold"],
        dimensions=["dealer_name"],
        filters={"vehicle_type": "Electric"},
        time_period="last_quarter",
    )
    sql = build_sql(plan, semantic_model)
    result = db_conn.execute(sql).fetchall()
    assert len(result) > 0


def test_sql_executes_revenue_by_sale_month(semantic_model, db_conn):
    """Verify STRFTIME translation works at runtime on DuckDB."""
    plan = QueryPlan(
        metrics=["total_revenue"],
        dimensions=["sale_month"],
    )
    sql = build_sql(plan, semantic_model)
    result = db_conn.execute(sql).fetchall()
    assert len(result) > 0
    # sale_month should be YYYY-MM format
    assert "-" in str(result[0][0])
