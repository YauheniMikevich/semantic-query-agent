import json
import os
import pathlib

import pytest
from langchain_core.messages import HumanMessage

from semantic_query_agent.agent import create_agent
from semantic_query_agent.database import create_database
from semantic_query_agent.semantic_model import load_semantic_model

ROOT = pathlib.Path(__file__).parent.parent
TEST_QUESTIONS_PATH = ROOT / "test_questions.json"
SEMANTIC_MODEL_PATH = ROOT / "semantic_model.yaml"

pytestmark = [
    pytest.mark.regression,
    pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set; skipping regression tests",
    ),
]


def _load_test_questions() -> list[dict]:
    with open(TEST_QUESTIONS_PATH) as f:
        return json.load(f)


def _round_floats(data: list[dict], precision: int = 2) -> list[dict]:
    """Round all float values in a list of dicts for stable comparison."""
    rounded = []
    for row in data:
        rounded.append({k: round(v, precision) if isinstance(v, float) else v for k, v in row.items()})
    return rounded


def _sort_results(data: list[dict]) -> list[dict]:
    """Sort list of dicts for order-independent comparison."""
    if not data:
        return data
    keys = sorted(data[0].keys())
    return sorted(data, key=lambda row: tuple(row.get(k, "") for k in keys))


@pytest.fixture(scope="module")
def agent():
    semantic_model = load_semantic_model(SEMANTIC_MODEL_PATH)
    db_conn = create_database()
    return create_agent(semantic_model, db_conn)


_questions = _load_test_questions()
_clear_questions = [q for q in _questions if q.get("expected_interpretation") is not None]
_ambiguous_questions = [q for q in _questions if q.get("expected_behavior") == "clarification_needed"]
_out_of_scope_questions = [q for q in _questions if q.get("expected_behavior") == "out_of_scope"]


@pytest.mark.parametrize("test_case", _clear_questions, ids=[f"Q{q['id']}" for q in _clear_questions])
async def test_clear_query(agent, test_case):
    """Q1-Q3: Assert interpretation and query results in a single invocation."""
    result = await agent.ainvoke({"messages": [HumanMessage(content=test_case["question"])]})

    # --- Interpretation assertions ---
    interpret = result["interpret_result"]
    assert interpret is not None, f"Q{test_case['id']}: interpret_result is None"
    assert interpret.query_plan is not None, f"Q{test_case['id']}: query_plan is None"

    expected = test_case["expected_interpretation"]
    plan = interpret.query_plan

    assert set(plan.metrics) == set(
        expected["metrics"]
    ), f"Q{test_case['id']}: metrics mismatch: {plan.metrics} != {expected['metrics']}"
    assert set(plan.dimensions) == set(
        expected["dimensions"]
    ), f"Q{test_case['id']}: dimensions mismatch: {plan.dimensions} != {expected['dimensions']}"
    assert (
        plan.filters == expected["filters"]
    ), f"Q{test_case['id']}: filters mismatch: {plan.filters} != {expected['filters']}"
    assert (
        plan.time_period == expected["time_period"]
    ), f"Q{test_case['id']}: time_period mismatch: {plan.time_period} != {expected['time_period']}"

    # --- Query results assertions ---
    actual_results = result.get("query_result")
    assert actual_results is not None, f"Q{test_case['id']}: query_result is None"

    expected_results = test_case["expected_results"]

    actual_sorted = _sort_results(_round_floats(actual_results))
    expected_sorted = _sort_results(_round_floats(expected_results))

    assert actual_sorted == expected_sorted, (
        f"Q{test_case['id']}: results mismatch:\n" f"  actual:   {actual_sorted}\n" f"  expected: {expected_sorted}"
    )


@pytest.mark.parametrize("test_case", _ambiguous_questions, ids=[f"Q{q['id']}" for q in _ambiguous_questions])
async def test_ambiguous_query(agent, test_case):
    """Q4: Assert ambiguous queries trigger clarification."""
    result = await agent.ainvoke({"messages": [HumanMessage(content=test_case["question"])]})

    interpret = result["interpret_result"]
    assert interpret is not None, f"Q{test_case['id']}: interpret_result is None"
    assert interpret.ambiguity_reason is not None, (
        f"Q{test_case['id']}: expected ambiguity_reason to be set, got None. "
        f"Plan: {interpret.query_plan}, is_out_of_scope: {interpret.is_out_of_scope}"
    )


@pytest.mark.parametrize("test_case", _out_of_scope_questions, ids=[f"Q{q['id']}" for q in _out_of_scope_questions])
async def test_out_of_scope_query(agent, test_case):
    """Q5: Assert out-of-scope queries are identified."""
    result = await agent.ainvoke({"messages": [HumanMessage(content=test_case["question"])]})

    interpret = result["interpret_result"]
    assert interpret is not None, f"Q{test_case['id']}: interpret_result is None"
    assert interpret.is_out_of_scope is True, (
        f"Q{test_case['id']}: expected is_out_of_scope=True, got {interpret.is_out_of_scope}. "
        f"Plan: {interpret.query_plan}, ambiguity_reason: {interpret.ambiguity_reason}"
    )
