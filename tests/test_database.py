from semantic_query_agent.database import create_database


def test_create_database_loads_data():
    conn = create_database()
    result = conn.execute("SELECT COUNT(*) FROM TRANSACTIONS").fetchone()
    assert result[0] == 500


def test_query_by_region():
    conn = create_database()
    result = conn.execute("SELECT DISTINCT region FROM TRANSACTIONS ORDER BY region").fetchall()
    regions = [r[0] for r in result]
    assert "Nordic" in regions
    assert "DACH" in regions


def test_query_electric_vehicles():
    conn = create_database()
    result = conn.execute(
        "SELECT COUNT(*) FROM TRANSACTIONS WHERE vehicle_type = 'Electric'"
    ).fetchone()
    assert result[0] > 0
