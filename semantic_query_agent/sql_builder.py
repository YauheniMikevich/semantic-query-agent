from semantic_query_agent.models import QueryPlan, SemanticModel

_SNOWFLAKE_TO_DUCKDB = {
    "TO_CHAR": "STRFTIME",
}


def _translate_expr(expr: str) -> str:
    """Translate Snowflake SQL expressions to DuckDB equivalents."""
    result = expr
    for snowflake_fn, duckdb_fn in _SNOWFLAKE_TO_DUCKDB.items():
        result = result.replace(snowflake_fn, duckdb_fn)
    return result


def _resolve_time_filter(time_period_name: str, model: SemanticModel) -> str:
    """Convert a time period name to a SQL WHERE clause fragment."""
    for tp in model.time_periods:
        if tp.name == time_period_name:
            return tp.filter
    raise ValueError(f"Unknown time period: {time_period_name}")


def build_sql(plan: QueryPlan, model: SemanticModel) -> str:
    """Build a DuckDB SQL query from a QueryPlan and SemanticModel."""
    metrics_map = {m.name: m for m in model.metrics}
    dimensions_map = {d.name: d for d in model.dimensions}

    # Validate metric names
    select_parts = []
    for metric_name in plan.metrics:
        if metric_name not in metrics_map:
            raise ValueError(f"Unknown metric: {metric_name}")
        metric = metrics_map[metric_name]
        select_parts.append(f"{_translate_expr(metric.expr)} AS {metric.name}")

    # Validate and add dimension expressions
    group_by_parts = []
    dimension_selects = []
    for dim_name in plan.dimensions:
        if dim_name not in dimensions_map:
            raise ValueError(f"Unknown dimension: {dim_name}")
        dim = dimensions_map[dim_name]
        translated = _translate_expr(dim.expr)
        dimension_selects.append(f"{translated} AS {dim.name}")
        group_by_parts.append(translated)

    # Build SELECT
    all_selects = dimension_selects + select_parts
    select_clause = ", ".join(all_selects)

    # Build WHERE
    where_parts = []
    if plan.time_period:
        time_filter = _resolve_time_filter(plan.time_period, model)
        where_parts.append(time_filter)

    for dim_name, dim_value in plan.filters.items():
        if dim_name not in dimensions_map:
            raise ValueError(f"Unknown dimension in filter: {dim_name}")
        dim = dimensions_map[dim_name]
        where_parts.append(f"{_translate_expr(dim.expr)} = '{dim_value}'")

    # Assemble SQL
    sql = f"SELECT {select_clause} FROM {model.base_table}"
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
    if group_by_parts:
        sql += " GROUP BY " + ", ".join(group_by_parts)

    # Order by first metric descending for ranked results
    if select_parts:
        sql += f" ORDER BY {plan.metrics[0]} DESC"

    return sql
