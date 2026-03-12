from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import HumanMessage
from pydantic import ValidationError

from semantic_query_agent.agent import create_agent
from semantic_query_agent.models import InterpretResult, QueryPlan


@pytest.mark.asyncio
async def test_clear_query_flow(semantic_model, db_conn):
    """Test: user asks a clear question -> INTERPRET -> ROUTE -> EXECUTE -> RESPOND."""
    mock_interpret_result = InterpretResult(
        query_plan=QueryPlan(
            metrics=["total_revenue"],
            dimensions=["region"],
            time_period="ytd",
        ),
        is_out_of_scope=False,
        ambiguity_reason=None,
        confidence_score=0.95,
    )

    with (
        patch("semantic_query_agent.agent.call_interpret", new_callable=AsyncMock) as mock_interpret,
        patch("semantic_query_agent.agent.call_respond", new_callable=AsyncMock) as mock_respond,
    ):
        mock_interpret.return_value = mock_interpret_result
        mock_respond.return_value = "Total revenue by region YTD: Nordic 5M, DACH 4M..."

        agent = create_agent(semantic_model, db_conn, max_validation_retries=1, confidence_threshold=0.7)
        result = await agent.ainvoke({"messages": [HumanMessage(content="Show total revenue by region YTD")]})

        assert result["response"] is not None
        assert mock_interpret.called
        assert mock_respond.called
        assert result["query_result"] is not None


@pytest.mark.asyncio
async def test_ambiguous_query_flow(semantic_model, db_conn):
    """Test: ambiguous question -> INTERPRET -> ROUTE -> CLARIFY."""
    mock_interpret_result = InterpretResult(
        query_plan=None,
        is_out_of_scope=False,
        ambiguity_reason="The query 'How are sales doing?' is ambiguous. Which metric (revenue, units sold, margins) and time period?",
        confidence_score=0.3,
    )

    with (
        patch("semantic_query_agent.agent.call_interpret", new_callable=AsyncMock) as mock_interpret,
        patch("semantic_query_agent.agent.call_clarify", new_callable=AsyncMock) as mock_clarify,
    ):
        mock_interpret.return_value = mock_interpret_result
        mock_clarify.return_value = "Could you clarify which metric you mean? Revenue, units sold, or margins?"

        agent = create_agent(semantic_model, db_conn, max_validation_retries=1, confidence_threshold=0.7)
        result = await agent.ainvoke({"messages": [HumanMessage(content="How are sales doing?")]})

        assert result["response"] is not None
        assert "clarif" in result["response"].lower() or "which" in result["response"].lower()
        assert result.get("query_result") is None


@pytest.mark.asyncio
async def test_out_of_scope_flow(semantic_model, db_conn):
    """Test: off-topic question -> INTERPRET -> ROUTE -> RESPOND (polite refusal)."""
    mock_interpret_result = InterpretResult(
        query_plan=None,
        is_out_of_scope=True,
        ambiguity_reason=None,
    )

    with (
        patch("semantic_query_agent.agent.call_interpret", new_callable=AsyncMock) as mock_interpret,
        patch("semantic_query_agent.agent.call_respond", new_callable=AsyncMock) as mock_respond,
    ):
        mock_interpret.return_value = mock_interpret_result
        mock_respond.return_value = "I can only answer questions about vehicle sales data."

        agent = create_agent(semantic_model, db_conn, max_validation_retries=1, confidence_threshold=0.7)
        result = await agent.ainvoke({"messages": [HumanMessage(content="What's the weather?")]})

        assert result["response"] is not None
        assert result.get("query_result") is None


@pytest.mark.asyncio
async def test_validation_retry_flow(semantic_model, db_conn):
    """Test: invalid plan -> ROUTE validates -> retry INTERPRET -> succeeds."""
    bad_result = InterpretResult(
        query_plan=QueryPlan(metrics=["revenue"], dimensions=["region"]),
        is_out_of_scope=False,
        ambiguity_reason=None,
        confidence_score=0.95,
    )
    good_result = InterpretResult(
        query_plan=QueryPlan(metrics=["total_revenue"], dimensions=["region"]),
        is_out_of_scope=False,
        ambiguity_reason=None,
        confidence_score=0.95,
    )

    with (
        patch("semantic_query_agent.agent.call_interpret", new_callable=AsyncMock) as mock_interpret,
        patch("semantic_query_agent.agent.call_respond", new_callable=AsyncMock) as mock_respond,
    ):
        mock_interpret.side_effect = [bad_result, good_result]
        mock_respond.return_value = "Total revenue by region: ..."

        agent = create_agent(semantic_model, db_conn, max_validation_retries=1, confidence_threshold=0.7)
        result = await agent.ainvoke({"messages": [HumanMessage(content="Show revenue by region")]})

        assert result["response"] is not None
        assert result["query_result"] is not None
        assert mock_interpret.call_count == 2


@pytest.mark.asyncio
async def test_validation_max_retry_then_respond(semantic_model, db_conn):
    """Test: invalid plan fails validation twice -> gives up and responds with error."""
    bad_result = InterpretResult(
        query_plan=QueryPlan(metrics=["nonexistent"], dimensions=["region"]),
        is_out_of_scope=False,
        ambiguity_reason=None,
        confidence_score=0.95,
    )

    with (
        patch("semantic_query_agent.agent.call_interpret", new_callable=AsyncMock) as mock_interpret,
        patch("semantic_query_agent.agent.call_respond", new_callable=AsyncMock) as mock_respond,
    ):
        mock_interpret.return_value = bad_result
        mock_respond.return_value = "I couldn't process that query."

        agent = create_agent(semantic_model, db_conn, max_validation_retries=1, confidence_threshold=0.7)
        result = await agent.ainvoke({"messages": [HumanMessage(content="Show me nonexistent data")]})

        assert result["response"] is not None
        assert mock_interpret.call_count == 2


@pytest.mark.asyncio
async def test_empty_results_flow(semantic_model, db_conn):
    """Test: valid query returns empty results -> RESPOND explains no data."""
    mock_interpret_result = InterpretResult(
        query_plan=QueryPlan(
            metrics=["total_revenue"],
            dimensions=["region"],
            filters={"region": "Antarctica"},
        ),
        is_out_of_scope=False,
        ambiguity_reason=None,
        confidence_score=0.95,
    )

    with (
        patch("semantic_query_agent.agent.call_interpret", new_callable=AsyncMock) as mock_interpret,
        patch("semantic_query_agent.agent.call_respond", new_callable=AsyncMock) as mock_respond,
    ):
        mock_interpret.return_value = mock_interpret_result
        mock_respond.return_value = "No data matched your query criteria."

        agent = create_agent(semantic_model, db_conn, max_validation_retries=1, confidence_threshold=0.7)
        result = await agent.ainvoke({"messages": [HumanMessage(content="Revenue in Antarctica")]})

        assert result["response"] is not None
        assert result["query_result"] == []


@pytest.mark.asyncio
async def test_low_confidence_routes_to_clarify(semantic_model, db_conn):
    """Test: valid plan with low confidence -> ROUTE -> CLARIFY instead of EXECUTE."""
    mock_interpret_result = InterpretResult(
        query_plan=QueryPlan(
            metrics=["total_revenue"],
            dimensions=["region"],
            time_period="ytd",
        ),
        is_out_of_scope=False,
        ambiguity_reason=None,
        confidence_score=0.5,
        confidence_reasoning="'How did regions do' could mean revenue, units sold, or margins",
    )

    with (
        patch("semantic_query_agent.agent.call_interpret", new_callable=AsyncMock) as mock_interpret,
        patch("semantic_query_agent.agent.call_clarify", new_callable=AsyncMock) as mock_clarify,
    ):
        mock_interpret.return_value = mock_interpret_result
        mock_clarify.return_value = "Could you clarify what metric you're interested in?"

        agent = create_agent(semantic_model, db_conn, max_validation_retries=1, confidence_threshold=0.7)
        result = await agent.ainvoke({"messages": [HumanMessage(content="How did regions do this year?")]})

        assert result["response"] is not None
        assert mock_clarify.called
        assert result.get("query_result") is None
        # Verify clarify received the confidence_reasoning as the ambiguity_reason
        call_args = mock_clarify.call_args
        assert "'How did regions do' could mean revenue, units sold, or margins" in call_args[0][1]


@pytest.mark.asyncio
async def test_high_confidence_routes_to_execute(semantic_model, db_conn):
    """Test: valid plan with high confidence -> ROUTE -> EXECUTE -> RESPOND."""
    mock_interpret_result = InterpretResult(
        query_plan=QueryPlan(
            metrics=["total_revenue"],
            dimensions=["region"],
            time_period="ytd",
        ),
        is_out_of_scope=False,
        ambiguity_reason=None,
        confidence_score=0.9,
    )

    with (
        patch("semantic_query_agent.agent.call_interpret", new_callable=AsyncMock) as mock_interpret,
        patch("semantic_query_agent.agent.call_respond", new_callable=AsyncMock) as mock_respond,
    ):
        mock_interpret.return_value = mock_interpret_result
        mock_respond.return_value = "Total revenue by region YTD: ..."

        agent = create_agent(semantic_model, db_conn, max_validation_retries=1, confidence_threshold=0.7)
        result = await agent.ainvoke({"messages": [HumanMessage(content="Show total revenue by region YTD")]})

        assert result["response"] is not None
        assert result["query_result"] is not None


@pytest.mark.asyncio
async def test_confidence_at_threshold_routes_to_execute(semantic_model, db_conn):
    """Test: confidence exactly at threshold (0.7) -> EXECUTE (threshold is exclusive)."""
    mock_interpret_result = InterpretResult(
        query_plan=QueryPlan(
            metrics=["total_revenue"],
            dimensions=["region"],
            time_period="ytd",
        ),
        is_out_of_scope=False,
        ambiguity_reason=None,
        confidence_score=0.7,
    )

    with (
        patch("semantic_query_agent.agent.call_interpret", new_callable=AsyncMock) as mock_interpret,
        patch("semantic_query_agent.agent.call_respond", new_callable=AsyncMock) as mock_respond,
    ):
        mock_interpret.return_value = mock_interpret_result
        mock_respond.return_value = "Total revenue by region YTD: ..."

        agent = create_agent(semantic_model, db_conn, max_validation_retries=1, confidence_threshold=0.7)
        result = await agent.ainvoke({"messages": [HumanMessage(content="Show total revenue by region YTD")]})

        assert result["response"] is not None
        assert result["query_result"] is not None


@pytest.mark.asyncio
async def test_ambiguity_reason_takes_precedence_over_low_confidence(semantic_model, db_conn):
    """Test: LLM sets ambiguity_reason AND low confidence -> CLARIFY uses ambiguity_reason."""
    mock_interpret_result = InterpretResult(
        query_plan=None,
        is_out_of_scope=False,
        ambiguity_reason="Which metric do you mean: revenue or units?",
        confidence_score=0.3,
        confidence_reasoning="Very uncertain interpretation",
    )

    with (
        patch("semantic_query_agent.agent.call_interpret", new_callable=AsyncMock) as mock_interpret,
        patch("semantic_query_agent.agent.call_clarify", new_callable=AsyncMock) as mock_clarify,
    ):
        mock_interpret.return_value = mock_interpret_result
        mock_clarify.return_value = "Which metric do you mean?"

        agent = create_agent(semantic_model, db_conn, max_validation_retries=1, confidence_threshold=0.7)
        result = await agent.ainvoke({"messages": [HumanMessage(content="How are sales?")]})

        assert result["response"] is not None
        assert mock_clarify.called
        # Verify clarify was called with the original ambiguity_reason, not confidence_reasoning
        mock_clarify.assert_called_once()
        call_args = mock_clarify.call_args
        assert "Which metric do you mean: revenue or units?" in call_args[0][1]


def test_confidence_score_validation_bounds():
    """Test that confidence_score enforces 0.0-1.0 bounds."""
    with pytest.raises(ValidationError):
        InterpretResult(confidence_score=1.5)
    with pytest.raises(ValidationError):
        InterpretResult(confidence_score=-0.1)

    # Valid bounds should work
    result = InterpretResult(confidence_score=0.0)
    assert result.confidence_score == 0.0
    result = InterpretResult(confidence_score=1.0)
    assert result.confidence_score == 1.0
