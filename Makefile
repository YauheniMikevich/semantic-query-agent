.PHONY: black isort flake8 mypy lint run test

black:
	poetry run black . || true

isort:
	poetry run isort . || true

flake8:
	poetry run flake8 . || true

lint: black isort flake8

run:
	poetry run uvicorn semantic_query_agent.main:app --reload --port 8000

test:
	poetry run pytest tests/ -v
