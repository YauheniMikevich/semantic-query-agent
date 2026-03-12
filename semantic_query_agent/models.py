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
