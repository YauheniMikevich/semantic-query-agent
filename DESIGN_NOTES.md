# Design Notes

## Grounding: How the LLM stays within the semantic model

The LLM never generates SQL directly. Instead, it produces a structured `QueryPlan` (metrics, dimensions, filters, time period) via OpenAI function calling, constrained to the Pydantic schema. The system prompt enumerates every metric, dimension, time period, and synonym from the YAML model, so the LLM selects from known fields rather than inventing them.

A deterministic **ROUTE** node then validates the plan against the semantic model before execution. If the LLM hallucinates a field name, the validator rejects it with an error listing valid options, and the agent retries INTERPRET once (or more if specified). Only validated plans reach the **SQL builder**, which maps field names to SQL expressions defined in the YAML — no LLM-generated SQL ever touches the database.

A third layer — **confidence scoring** — catches cases where the plan is structurally valid but semantically uncertain. The LLM emits a `confidence_score` (0.0–1.0) alongside the plan; the ROUTE node reroutes plans below a configurable threshold (default 0.7) to the CLARIFY node instead of executing them.

Together, these three layers (structured output + validation + confidence gating) ensure the LLM is grounded at generation, execution, and interpretation-quality time.

## Guardrails: What to add for production

- **Output validation against source data.** After query execution, cross-check that returned aggregates (totals, averages) are arithmetically consistent with the raw result set to catch cases where a structurally valid plan produces misleading numbers.
- **Hallucination circuit-breaker.** Track per-session validation failure and low-confidence rates; if they exceed a threshold, halt the session and escalate to a human rather than letting the LLM keep retrying.
- **Regression testing.** Run the 5 test questions (plus a growing golden set) in CI against every model or prompt change to catch interpretation regressions early.
- **Input/output content filtering.** Screen user prompts for injection attempts and LLM responses for PII or data leakage before returning results.
- **Query sandboxing.** Run generated SQL with a read-only role, statement timeouts, and row limits to prevent resource exhaustion.
- **Observability.** Log every query plan, generated SQL, validation outcome, and LLM latency. Surface anomalies (high retry rates, frequent low-confidence scores) to detect drift or misuse.

## Teams Integration: How to expose this as a Microsoft Teams Copilot agent

The agent would be surfaced as a **bot-based message extension agent** for Microsoft 365 Copilot, built with the **Microsoft 365 Agents SDK** (the successor to the now-archived Bot Framework SDK):

1. **Bot registration.** Register an Azure Bot resource (single-tenant); expose an `/api/messages` endpoint that receives Bot Framework Activity objects, extracts the user query, runs it through the agent pipeline, and replies with the result.
2. **Adaptive Cards for rich output.** Format query results as Adaptive Cards using the `Table` element and native chart types (`Chart.VerticalBar`, `Chart.Donut`, etc.) so answers render inline in Teams.
3. **Authentication.** Enable Azure AD SSO via the Bot Framework token service so the agent identifies the caller and can enforce row-level data-access policies.
4. **Multi-turn context.** Map the Teams conversation ID to the existing `session_id` to preserve clarification and follow-up state across messages.
5. **Manifest and deployment.** Package as a Teams app (manifest.json + icons), publish to the organization app catalog, and register the bot as a Copilot message extension agent so users can invoke it with `@SalesAgent` inside Microsoft 365 Copilot.
