# Design Notes

## Grounding: How the LLM stays within the semantic model

The LLM never generates SQL directly. Instead, it produces a structured `QueryPlan` (metrics, dimensions, filters, time period) via OpenAI function calling, constrained to the Pydantic schema. The system prompt enumerates every metric, dimension, time period, and synonym from the YAML model, so the LLM selects from known fields rather than inventing them.

A deterministic **ROUTE** node then validates the plan against the semantic model before execution. If the LLM hallucinates a field name, the validator rejects it with an error listing valid options, and the agent retries INTERPRET once (or more if specified). Only validated plans reach the **SQL builder**, which maps field names to SQL expressions defined in the YAML — no LLM-generated SQL ever touches the database.

This two-layer approach (structured output + post-hoc validation) ensures the LLM is grounded by the semantic model at both generation and execution time.

## Guardrails: What to add for production

- **Row-level security and query sandboxing.** Run generated SQL with a read-only role, statement timeouts, and row limits to prevent resource exhaustion.
- **Input/output content filtering.** Screen user prompts for injection attempts and LLM responses for PII or data leakage before returning results.
- **Parameterized queries.** Filter values are already parameterized (not string-interpolated) to prevent SQL injection from adversarial LLM output.
- **Observability.** Log every query plan, generated SQL, validation outcome, and LLM latency. Surface anomalies (high retry rates, frequent out-of-scope rejections) to detect drift or misuse.
- **Confidence scoring.** Have the LLM emit a confidence score alongside the query plan; flag low-confidence interpretations for human review or automatic clarification.
- **Rate limiting and authentication.** Per-user API keys, request quotas, and session expiry.
- **Regression testing.** Run the 5 test questions (plus a growing golden set) in CI against every model or prompt change to catch interpretation regressions early.

## Teams Integration: Exposing as a Microsoft Teams Copilot agent

The agent would be wrapped as a **Teams Message Extension** (or Copilot plugin) using the Bot Framework SDK:

1. **Bot registration.** Register an Azure Bot resource; configure the messaging endpoint to point at the existing FastAPI `/query` route (or a thin adapter that translates Bot Framework activities to the current `QueryRequest`/`QueryResponse` schema).
2. **Adaptive Cards for rich output.** Instead of plain text, format query results as Adaptive Cards with tables and charts, sent back as bot reply activities.
3. **Authentication.** Use Azure AD SSO via the Bot Framework's OAuth flow so the agent knows who is asking and can enforce data-access policies.
4. **Multi-turn in Teams.** Map the Teams conversation ID to the existing `session_id` to preserve multi-turn context (clarification follow-ups work naturally).
5. **Manifest and deployment.** Package the bot as a Teams app (manifest.json + icons), publish to the organization's app catalog, and optionally surface it as a Copilot plugin so users can invoke it with `@SalesAgent` in any Teams chat.
