from pydantic import BaseModel, Field

# --- Semantic Model YAML structures ---


class Metric(BaseModel):
    name: str
    display_name: str
    description: str
    expr: str
    data_type: str
    default_aggregation: str


class Dimension(BaseModel):
    name: str
    display_name: str
    description: str
    expr: str
    data_type: str
    allowed_values: list[str] | None = None


class TimeDimension(BaseModel):
    name: str
    display_name: str
    description: str
    expr: str
    data_type: str


class TimePeriod(BaseModel):
    name: str
    description: str
    filter: str


class Synonym(BaseModel):
    term: str
    maps_to: str
    value: str | None = None
    note: str | None = None


class SampleQuestion(BaseModel):
    question: str
    metrics: list[str]
    dimensions: list[str] = Field(default_factory=list)
    filters: dict[str, str] | None = None
    time_period: str | None = None


class SemanticModel(BaseModel):
    name: str
    description: str
    database: str
    schema_name: str = Field(alias="schema")
    base_table: str
    metrics: list[Metric]
    dimensions: list[Dimension]
    time_dimension: TimeDimension
    time_periods: list[TimePeriod]
    synonyms: list[Synonym]
    sample_questions: list[SampleQuestion] = Field(default_factory=list)


# --- Query Plan (INTERPRET node output) ---


class QueryPlan(BaseModel):
    """Structured representation of what the user wants to query."""

    metrics: list[str] = Field(description="List of metric names to compute (from semantic model)")
    dimensions: list[str] = Field(default_factory=list, description="List of dimension names to group by")
    filters: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Dimension name -> value to filter on. "
            "When the user mentions a specific category (e.g. 'electric vehicles'), "
            "map it to the corresponding dimension and value from the synonym list "
            "(e.g. {'vehicle_type': 'Electric'})."
        ),
    )
    time_period: str | None = Field(default=None, description="Time period name (e.g. 'last_quarter', 'ytd')")


class InterpretResult(BaseModel):
    """Output of the INTERPRET node."""

    query_plan: QueryPlan | None = Field(
        default=None, description="The parsed query plan, None if ambiguous or out of scope"
    )
    is_out_of_scope: bool = Field(default=False, description="True if the question is not about vehicle sales")
    ambiguity_reason: str | None = Field(
        default=None, description="Explanation of why clarification is needed, None if query is clear"
    )
    confidence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in the interpretation, 0.0 (no confidence) to 1.0 (fully confident)",
    )
    confidence_reasoning: str | None = Field(
        default=None,
        description="Explanation of uncertainty factors when confidence is below 1.0",
    )


# --- API schemas ---


class QueryRequest(BaseModel):
    session_id: str
    message: str


class QueryResponse(BaseModel):
    response: str
