from semantic_query_agent.models import Dimension, Metric, Synonym, TimePeriod


def test_metric_creation():
    m = Metric(
        name="total_revenue",
        display_name="Total Revenue",
        description="Total sales revenue in EUR",
        expr="SUM(sale_price_eur)",
        data_type="NUMBER",
        default_aggregation="SUM",
    )
    assert m.name == "total_revenue"
    assert m.expr == "SUM(sale_price_eur)"


def test_synonym_with_value():
    s = Synonym(term="electric", maps_to="vehicle_type", value="Electric")
    assert s.term == "electric"
    assert s.value == "Electric"


def test_synonym_without_value():
    s = Synonym(term="revenue", maps_to="total_revenue")
    assert s.value is None
    assert s.note is None
