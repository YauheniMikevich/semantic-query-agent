.PHONY: black isort flake8 lint black-check isort-check lint-check run test

black:
	poetry run black . || true

isort:
	poetry run isort . || true

flake8:
	poetry run flake8 . || true

lint: black isort flake8

black-check:
	poetry run black --check .

isort-check:
	poetry run isort --check-only .

lint-check: black-check isort-check flake8

run:
	poetry run uvicorn semantic_query_agent.main:app --reload --port 8000

test:
	poetry run pytest tests/ -v

demo:
	poetry run python run_test_questions.py
