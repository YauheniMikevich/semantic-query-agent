import pathlib

import yaml

from semantic_query_agent.models import SemanticModel


def load_semantic_model(path: pathlib.Path) -> SemanticModel:
    with open(path) as f:
        data = yaml.safe_load(f)
    return SemanticModel.model_validate(data)
