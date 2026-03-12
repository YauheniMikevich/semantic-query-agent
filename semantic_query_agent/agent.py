from typing import Annotated

import duckdb
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel

from semantic_query_agent.config import get_settings
from semantic_query_agent.models import InterpretResult, QueryPlan, SemanticModel
from semantic_query_agent.prompts import RESPOND_SYSTEM_PROMPT, build_interpret_system_prompt
from semantic_query_agent.sql_builder import build_sql

# --- Agent State ---


class AgentState(BaseModel):
    messages: Annotated[list[BaseMessage], add_messages] = []
    interpret_result: InterpretResult | None = None
    query_result: list[dict] | None = None
    response: str | None = None
    error: str | None = None
    validation_error: str | None = None
    retry_count: int = 0


# --- Runtime dependencies (set by create_agent) ---

_semantic_model: SemanticModel | None = None
_db_conn: duckdb.DuckDBPyConnection | None = None
_system_prompt: str | None = None
_max_validation_retries: int = 1


# --- LLM Call Wrappers (mockable in tests) ---


async def call_interpret(messages: list[BaseMessage], system_prompt: str) -> InterpretResult:
    """Call GPT-4o to interpret the user's query into a structured plan."""
    settings = get_settings()
    llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)
    structured_llm = llm.with_structured_output(InterpretResult)
    response = await structured_llm.ainvoke([SystemMessage(content=system_prompt)] + messages)
    return response


async def call_respond(messages: list[BaseMessage], query_result: list[dict] | None, error: str | None) -> str:
    """Call GPT-4o to format query results into a natural language response."""
    settings = get_settings()
    llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)

    if error:
        context = f"An error occurred while processing the query: {error}. Please tell the user you couldn't process their request and suggest they rephrase."
    elif query_result is not None:
        context = f"Query results:\n{query_result}\n\nFormat these results into a clear, natural language response."
    else:
        context = (
            "The user asked an out-of-scope question. Politely explain you can only help with vehicle sales analytics."
        )

    response = await llm.ainvoke(
        [SystemMessage(content=RESPOND_SYSTEM_PROMPT)] + messages + [SystemMessage(content=context)]
    )
    return response.content


# --- Node Functions ---


async def interpret_node(state: AgentState) -> dict:
    """Interpret the user's query into a structured plan."""
    messages = list(state.messages)
    if state.validation_error:
        messages.append(
            SystemMessage(
                content=f"Your previous query plan was invalid: {state.validation_error}. "
                "Please fix the metric/dimension/time period names and try again.",
            )
        )
    result = await call_interpret(messages, _system_prompt)
    return {"interpret_result": result}


def _validate_query_plan(plan: QueryPlan, model: SemanticModel) -> str | None:
    """Validate that all metric/dimension/time period names in the plan exist in the semantic model.

    Returns None if valid, or an error message string if invalid.
    """
    metric_names = {m.name for m in model.metrics}
    dimension_names = {d.name for d in model.dimensions}
    time_period_names = {tp.name for tp in model.time_periods}

    errors = []
    for m in plan.metrics:
        if m not in metric_names:
            errors.append(f"Unknown metric '{m}'. Available: {', '.join(sorted(metric_names))}")
    for d in plan.dimensions:
        if d not in dimension_names:
            errors.append(f"Unknown dimension '{d}'. Available: {', '.join(sorted(dimension_names))}")
    for d in plan.filters:
        if d not in dimension_names:
            errors.append(f"Unknown filter dimension '{d}'. Available: {', '.join(sorted(dimension_names))}")
    if plan.time_period and plan.time_period not in time_period_names:
        errors.append(f"Unknown time period '{plan.time_period}'. Available: {', '.join(sorted(time_period_names))}")

    return "; ".join(errors) if errors else None


def route_node(state: AgentState) -> dict:
    """Deterministic router with query plan validation — no LLM call."""
    result = state.interpret_result
    if result is None or result.is_out_of_scope:
        return {"validation_error": None}
    if result.ambiguity_reason:
        return {"validation_error": None}
    if result.query_plan:
        error = _validate_query_plan(result.query_plan, _semantic_model)
        if error:
            return {"validation_error": error, "retry_count": state.retry_count + 1}
        return {"validation_error": None}
    return {"validation_error": None}


def route_after_validation(state: AgentState) -> str:
    """Conditional edge function after ROUTE node."""
    result = state.interpret_result
    if result is None or result.is_out_of_scope:
        return "respond"
    if result.ambiguity_reason:
        return "clarify"
    if state.validation_error:
        if state.retry_count > _max_validation_retries:
            return "respond"
        return "interpret"
    if result.query_plan:
        return "execute"
    return "respond"


def clarify_node(state: AgentState) -> dict:
    """Format the ambiguity reason into a clarification response."""
    return {"response": state.interpret_result.ambiguity_reason}


def execute_node(state: AgentState) -> dict:
    """Execute the SQL query against DuckDB."""
    plan = state.interpret_result.query_plan
    try:
        sql = build_sql(plan, _semantic_model)
        rows = _db_conn.execute(sql).fetchall()
        columns = [desc[0] for desc in _db_conn.description]
        query_result = [dict(zip(columns, row)) for row in rows]
        return {"query_result": query_result}
    except duckdb.Error as e:
        return {"error": str(e)}


async def respond_node(state: AgentState) -> dict:
    """Call LLM to format results into natural language."""
    error = state.error or state.validation_error
    response = await call_respond(
        state.messages,
        state.query_result,
        error,
    )
    return {"response": response}


# --- Graph Assembly ---


def create_agent(
    semantic_model: SemanticModel,
    db_conn: duckdb.DuckDBPyConnection,
    max_validation_retries: int | None = None,
):
    """Build and compile the LangGraph agent."""
    global _semantic_model, _db_conn, _system_prompt, _max_validation_retries

    _semantic_model = semantic_model
    _db_conn = db_conn
    _system_prompt = build_interpret_system_prompt(semantic_model)

    if max_validation_retries is None:
        _max_validation_retries = get_settings().max_validation_retries
    else:
        _max_validation_retries = max_validation_retries

    workflow = StateGraph(AgentState)

    workflow.add_node("interpret", interpret_node)
    workflow.add_node("route", route_node)
    workflow.add_node("clarify", clarify_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("respond", respond_node)

    workflow.add_edge(START, "interpret")
    workflow.add_edge("interpret", "route")
    workflow.add_conditional_edges(
        "route",
        route_after_validation,
        {
            "execute": "execute",
            "clarify": "clarify",
            "respond": "respond",
            "interpret": "interpret",
        },
    )
    workflow.add_edge("clarify", END)
    workflow.add_edge("execute", "respond")
    workflow.add_edge("respond", END)

    return workflow.compile()
