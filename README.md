# Semantic Query Agent

A LangGraph-based agent that translates natural language questions about vehicle sales into SQL queries against a semantic model, executed on DuckDB. Exposed via FastAPI with a minimal chat frontend.

**Tech stack:** Python 3.11, LangGraph, LangChain-OpenAI (GPT-4o), DuckDB, FastAPI, Pydantic, Poetry

## Architecture

```mermaid
graph LR
    User["User (Chat UI)"] <-->|HTTP| FastAPI
    FastAPI <--> Agent["LangGraph Agent"]
    Agent -.->|LLM calls| OpenAI["OpenAI GPT-4o"]
    Agent -->|reads| SemanticModel["Semantic Model (YAML)"]
    Agent -->|queries| DuckDB["DuckDB (sales_data.json)"]
```

### Agent State Machine

```mermaid
stateDiagram-v2
    [*] --> INTERPRET
    INTERPRET --> ROUTE
    ROUTE --> EXECUTE : valid query plan
    ROUTE --> CLARIFY : ambiguous
    ROUTE --> RESPOND : out of scope
    ROUTE --> INTERPRET : invalid plan\n(retry, max 1)
    EXECUTE --> RESPOND
    CLARIFY --> [*] : return clarification question
    RESPOND --> [*] : return answer
```

- **INTERPRET** — LLM extracts a structured query plan (metrics, dimensions, filters, time range) from user input, grounded by the semantic model and its synonym map.
- **ROUTE** — Pure Python. Validates the query plan against the semantic model. Routes to EXECUTE, CLARIFY, or RESPOND. Retries INTERPRET once on validation failure.
- **EXECUTE** — Deterministic SQL builder maps query plan fields to SQL expressions from the YAML model. No LLM-generated SQL.
- **CLARIFY** — Returns a follow-up question. The graph exits; the next user message re-enters at INTERPRET with full history.
- **RESPOND** — LLM formats query results into a natural language answer, or handles out-of-scope/error cases.

Only INTERPRET and RESPOND call the LLM. ROUTE and EXECUTE are deterministic.

### Semantic Model

The YAML model (`semantic_model.yaml`) defines metrics, dimensions, time periods, and synonyms for a vehicle sales dataset. It serves dual purpose: LLM grounding in the system prompt and SQL expression source for the builder.

## Getting Started

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/)
- OpenAI API key

### Setup

```bash
# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Run

```bash
make run
# → starts uvicorn on http://localhost:8000
```

Open http://localhost:8000 in your browser for the chat UI.

### Docker

```bash
# Make sure .env is configured, then:
docker compose up --build
```

### API

- `POST /query` — `{ "session_id": "...", "message": "..." }` → `{ "response": "..." }`
- `GET /health` — health check

### Test & Lint

```bash
make test    # pytest
make lint    # black + isort + flake8
```

## Project Structure

```
semantic_query_agent/
├── main.py              # FastAPI app, endpoints, startup
├── agent.py             # LangGraph state machine, nodes
├── models.py            # Pydantic models (state, query plan, API schemas)
├── semantic_model.py    # YAML loader, Pydantic models for metrics/dimensions
├── sql_builder.py       # QueryPlan → SQL string
├── config.py            # Pydantic BaseSettings from .env
└── prompts.py           # System prompts for INTERPRET and RESPOND nodes
static/
└── index.html           # Chat frontend (vanilla JS)
tests/
├── test_semantic_model.py
├── test_sql_builder.py
├── test_agent.py
└── test_api.py
```

## Limitations

- **No persistence** — sessions are in-memory; server restart clears all conversation history
- **No authentication or rate limiting**
- **No streaming responses** — full response returned after all processing completes
- **Single-process** — in-memory session store doesn't scale horizontally
- **Time periods are computed relative to the dataset's max date**, not the current wall clock
- **DuckDB dialect only** — the YAML model uses Snowflake syntax (`TO_CHAR`), which the SQL builder translates to DuckDB equivalents (`STRFTIME`) at runtime
