# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

RUN pip install --no-cache-dir poetry==2.1.3

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.in-project true && \
    poetry install --only main --no-interaction --no-ansi

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

COPY semantic_query_agent/ semantic_query_agent/
COPY static/ static/
COPY semantic_model.yaml sales_data.json ./

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "semantic_query_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
