import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from semantic_query_agent.agent import create_agent
from semantic_query_agent.database import create_database
from semantic_query_agent.models import QueryRequest, QueryResponse
from semantic_query_agent.semantic_model import load_semantic_model

# --- Global state ---
_agent = None
_sessions: dict[str, list[BaseMessage]] = {}

SEMANTIC_MODEL_PATH = pathlib.Path(__file__).parent.parent / "semantic_model.yaml"
STATIC_PATH = pathlib.Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent
    semantic_model = load_semantic_model(SEMANTIC_MODEL_PATH)
    db_conn = create_database()
    _agent = create_agent(semantic_model, db_conn)
    yield


app = FastAPI(title="Semantic Query Agent", lifespan=lifespan)


async def process_query(session_id: str, message: str) -> str:
    """Run the agent graph for a user message within a session."""
    if session_id not in _sessions:
        _sessions[session_id] = []

    _sessions[session_id].append(HumanMessage(content=message))

    result = await _agent.ainvoke({"messages": _sessions[session_id]})
    response_text = result["response"]

    _sessions[session_id].append(AIMessage(content=response_text))

    return response_text


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    response_text = await process_query(request.session_id, request.message)
    return QueryResponse(response=response_text)


# Mount static files last (so API routes take priority)
if STATIC_PATH.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_PATH), html=True), name="static")
