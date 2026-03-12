.PHONY: black isort flake8 mypy lint

black:
	poetry run black . || true

isort:
	poetry run isort . || true

flake8:
	poetry run flake8 . || true

lint: black isort flake8
