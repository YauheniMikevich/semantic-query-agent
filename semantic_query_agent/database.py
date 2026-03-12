import pathlib

import duckdb

DATA_PATH = pathlib.Path(__file__).parent.parent / "sales_data.json"


def create_database(data_path: pathlib.Path = DATA_PATH) -> duckdb.DuckDBPyConnection:
    """Create an in-memory DuckDB database loaded with sales data."""
    conn = duckdb.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE TRANSACTIONS AS
        SELECT
            transaction_id::VARCHAR AS transaction_id,
            sale_date::DATE AS sale_date,
            region::VARCHAR AS region,
            vehicle_model::VARCHAR AS vehicle_model,
            vehicle_type::VARCHAR AS vehicle_type,
            dealer_name::VARCHAR AS dealer_name,
            customer_segment::VARCHAR AS customer_segment,
            cost_eur::DOUBLE AS cost_eur,
            sale_price_eur::DOUBLE AS sale_price_eur,
            days_on_lot::INTEGER AS days_on_lot
        FROM read_json_auto(?)
        """,
        [str(data_path)],
    )
    return conn
