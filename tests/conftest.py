import os
import pathlib

import pytest

from semantic_query_agent.database import create_database
from semantic_query_agent.semantic_model import load_semantic_model


@pytest.fixture(autouse=True)
def _set_dummy_api_key(monkeypatch):
    """Set a dummy OpenAI API key so SemanticQueryAgent can be constructed in CI."""
    monkeypatch.setenv("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", "test-key"))


@pytest.fixture
def semantic_model():
    path = pathlib.Path(__file__).parent.parent / "semantic_model.yaml"
    return load_semantic_model(path)


@pytest.fixture
def db_conn():
    return create_database()
