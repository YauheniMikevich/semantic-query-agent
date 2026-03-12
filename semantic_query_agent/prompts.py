from semantic_query_agent.models import SemanticModel


def build_interpret_system_prompt(model: SemanticModel) -> str:
    """Build the system prompt for the INTERPRET node.

    Includes all metrics, dimensions, time periods, and synonyms
    so the LLM can match user queries to the semantic model.
    """
    metrics_section = "\n".join(
        f"  - {m.name}: {m.description} (expr: {m.expr})" for m in model.metrics
    )
    dimensions_section = "\n".join(
        f"  - {d.name}: {d.description}"
        + (f" (allowed values: {', '.join(d.allowed_values)})" if d.allowed_values else "")
        for d in model.dimensions
    )
    time_periods_section = "\n".join(
        f"  - {tp.name}: {tp.description}" for tp in model.time_periods
    )
    synonyms_section = "\n".join(
        f"  - \"{s.term}\" -> {s.maps_to}" + (f" (value: {s.value})" if s.value else "")
        for s in model.synonyms
    )

    return f"""You are a vehicle sales analytics assistant. Your job is to interpret natural language questions and extract a structured query plan.

You have access to the following semantic model:

METRICS (quantitative measures you can compute):
{metrics_section}

DIMENSIONS (categorical attributes you can group by or filter on):
{dimensions_section}

TIME PERIODS (predefined time ranges):
{time_periods_section}

SYNONYMS (alternative terms users might use):
{synonyms_section}

INSTRUCTIONS:
1. If the user asks a clear analytics question, extract the metrics, dimensions, filters, and time period.
2. If the user's question is ambiguous (e.g., "How are sales doing?" without specifying metric or time period), set ambiguity_reason explaining what needs clarification. Do NOT guess.
3. If the question is not about vehicle sales analytics at all, set is_out_of_scope to true.
4. When a synonym has a "value" (e.g., "electric" -> vehicle_type with value "Electric"), include it as a filter: {{"vehicle_type": "Electric"}}.
5. Use metric and dimension names exactly as listed above in your query plan."""


RESPOND_SYSTEM_PROMPT = """You are a vehicle sales analytics assistant. Format the query results into a clear, natural language response.

INSTRUCTIONS:
1. Present the data in a readable way. Use bullet points or a brief summary as appropriate.
2. Include the actual numbers from the results.
3. If the results are empty, explain that no data matched the query criteria.
4. Keep responses concise but informative.
5. If this is an out-of-scope response, politely explain that you can only answer questions about vehicle sales data (revenue, units sold, margins, etc. by region, model, dealer, etc.)."""
