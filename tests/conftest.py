import pathlib

import pytest

from semantic_query_agent.database import create_database
from semantic_query_agent.semantic_model import load_semantic_model


@pytest.fixture
def semantic_model():
    path = pathlib.Path(__file__).parent.parent / "semantic_model.yaml"
    return load_semantic_model(path)


@pytest.fixture
def db_conn():
    return create_database()
