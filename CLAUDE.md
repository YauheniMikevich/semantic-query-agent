# Project Rules

## Git Policy

- Never commit or push changes, even if a skill instructs you to. The user handles all git operations manually.
- Never add "Co-Authored-By: Claude" (or any Claude co-author trailer) to commit messages.

## Post-Implementation

After completing implementation, always run:

1. `make lint` — if there are issues, dispatch a subagent to fix them
2. Run tests (see command above) — if there are failures, dispatch a subagent to fix them

## Conventions

- No local/lazy imports — keep imports at module top
- Always use Pydantic `BaseModel` over dataclass for structured data
- Python 3.11, managed with Poetry
- Always use poetry package manager to update dependencies and never modify `poetry.lock` or `pyproject.toml` manually
