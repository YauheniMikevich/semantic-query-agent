# Task: Semantic Query Agent

## The Challenge

Build a minimal agent that translates natural language business questions into structured semantic queries.

Enterprises increasingly use semantic layers to provide consistent business definitions across analytics tools. The task is to build the AI reasoning component that maps natural language to these defined semantics.

Specifically:

- Parse business questions using an LLM
- Map intent to a provided semantic model (Snowflake Cortex Analyst YAML format)
- Execute against local mock data (pandas or DuckDB)
- Return results with natural language summary

## Provided Materials

| File | Description |
|------|-------------|
| `semantic_model.yaml` | Semantic model definition (Snowflake Cortex Analyst format) |
| `sales_data.json` | Mock transaction data (500 records) |
| `test_questions.json` | 5 test questions with expected outputs |

## Primary Test Case

**Input:**

> "What was our average deal margin by region last quarter?"

**Expected behavior:**

- Parse intent -> metric: `avg_deal_margin`, dimension: `region`, time: `last_quarter`
- Execute query against mock data
- Return structured results + natural language summary

**Expected output format** (example values are illustrative):

```json
{
  "interpretation": {
    "metrics": ["avg_deal_margin"],
    "dimensions": ["region"],
    "filters": {}
  },
  "results": [
    {"region": "Nordic", "avg_deal_margin": 12.3},
    {"region": "DACH", "avg_deal_margin": 10.8}
  ],
  "summary": "In Q3 2025, Nordic had the highest average deal margin at 12.3%."
}
```

## Requirements

### Must Have

- Handles all 5 test questions correctly
- Uses the semantic model to ground LLM responses (not ad-hoc field guessing)
- Asks clarifying questions for ambiguous requests
- Rejects out-of-scope questions gracefully

### Nice to Have

- Handles synonyms defined in semantic model
- Confidence scoring
- Multi-turn conversation support

## Deliverables

### 1. Working Code

Python script or notebook that: loads the semantic model, processes the 5 test questions, outputs structured results.

### 2. Design Notes (1 page max)

- **Grounding:** How do you ensure the LLM only uses metrics/dimensions from the semantic model?
- **Guardrails:** What would you add for production (hallucination prevention, validation)?
- **Teams Integration:** How would you expose this as a Microsoft Teams Copilot agent? (Conceptual -- no code required)

## Technical Notes

- **LLM:** Use any (OpenAI, Anthropic, local). Include setup instructions.
- **Execution:** Run locally with pandas or DuckDB -- no Snowflake account needed.
- **Reference date:** Use 2025-11-18 as "today" for time calculations.
- **Time periods:** "Last quarter" = Q3 2025 (Jul-Sep), "YTD" = Jan-Nov 2025.
