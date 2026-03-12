import json
import pathlib

import duckdb


DATA_PATH = pathlib.Path(__file__).parent.parent / "sales_data.json"


def create_database(data_path: pathlib.Path = DATA_PATH) -> duckdb.DuckDBPyConnection:
    """Create an in-memory DuckDB database loaded with sales data."""
    conn = duckdb.connect(":memory:")

    with open(data_path) as f:
        data = json.load(f)

    conn.execute("""
        CREATE TABLE TRANSACTIONS (
            transaction_id VARCHAR,
            sale_date DATE,
            region VARCHAR,
            vehicle_model VARCHAR,
            vehicle_type VARCHAR,
            dealer_name VARCHAR,
            customer_segment VARCHAR,
            cost_eur DOUBLE,
            sale_price_eur DOUBLE,
            days_on_lot INTEGER
        )
    """)

    for row in data:
        conn.execute(
            "INSERT INTO TRANSACTIONS VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                row["transaction_id"],
                row["sale_date"],
                row["region"],
                row["vehicle_model"],
                row["vehicle_type"],
                row["dealer_name"],
                row["customer_segment"],
                row["cost_eur"],
                row["sale_price_eur"],
                row["days_on_lot"],
            ],
        )

    return conn
