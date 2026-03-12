import pathlib

from semantic_query_agent.models import Metric, Synonym
from semantic_query_agent.semantic_model import load_semantic_model


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


def test_load_semantic_model_from_yaml():
    path = pathlib.Path(__file__).parent.parent / "semantic_model.yaml"
    model = load_semantic_model(path)
    assert model.name == "vehicle_sales_analytics"
    assert model.base_table == "TRANSACTIONS"
    assert len(model.metrics) == 6
    assert len(model.dimensions) == 7
    assert len(model.time_periods) == 5
    assert len(model.synonyms) > 0


def test_synonym_lookup():
    path = pathlib.Path(__file__).parent.parent / "semantic_model.yaml"
    model = load_semantic_model(path)
    electric_synonyms = [s for s in model.synonyms if s.term == "electric"]
    assert len(electric_synonyms) == 1
    assert electric_synonyms[0].maps_to == "vehicle_type"
    assert electric_synonyms[0].value == "Electric"


def test_metric_lookup_by_name():
    path = pathlib.Path(__file__).parent.parent / "semantic_model.yaml"
    model = load_semantic_model(path)
    revenue = next(m for m in model.metrics if m.name == "total_revenue")
    assert revenue.expr == "SUM(sale_price_eur)"
