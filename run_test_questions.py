"""Run all 5 test questions through the agent and print structured results.

Usage:
    poetry run python run_test_questions.py
"""

import asyncio
import json
import pathlib

from langchain_core.messages import HumanMessage

from semantic_query_agent.agent import create_agent
from semantic_query_agent.database import create_database
from semantic_query_agent.semantic_model import load_semantic_model

ROOT = pathlib.Path(__file__).parent
SEMANTIC_MODEL_PATH = ROOT / "semantic_model.yaml"
TEST_QUESTIONS_PATH = ROOT / "test_questions.json"


async def main() -> None:
    semantic_model = load_semantic_model(SEMANTIC_MODEL_PATH)
    db_conn = create_database()
    agent = create_agent(semantic_model, db_conn)

    with open(TEST_QUESTIONS_PATH) as f:
        test_questions = json.load(f)

    for tq in test_questions:
        question = tq["question"]
        print(f"\n{'=' * 70}")
        print(f"Question {tq['id']}: {question}")
        print("=" * 70)

        result = await agent.ainvoke({"messages": [HumanMessage(content=question)]})

        interpret = result.get("interpret_result")
        output: dict = {}

        if interpret and interpret.query_plan:
            plan = interpret.query_plan
            output["interpretation"] = {
                "metrics": plan.metrics,
                "dimensions": plan.dimensions,
                "filters": plan.filters,
                "time_period": plan.time_period,
            }
        elif interpret and interpret.ambiguity_reason:
            output["interpretation"] = None
            output["behavior"] = "clarification_needed"
        elif interpret and interpret.is_out_of_scope:
            output["interpretation"] = None
            output["behavior"] = "out_of_scope"

        if result.get("query_result") is not None:
            output["results"] = result["query_result"]

        output["summary"] = result.get("response")

        print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
