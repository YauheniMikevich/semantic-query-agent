from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from semantic_query_agent.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_query_endpoint_returns_response(client):
    with patch("semantic_query_agent.main.process_query", new_callable=AsyncMock) as mock_process:
        mock_process.return_value = "Total revenue by region: Nordic 5M..."
        response = await client.post(
            "/query",
            json={"session_id": "test-session", "message": "Show revenue by region"},
        )
        assert response.status_code == 200
        assert "response" in response.json()


@pytest.mark.asyncio
async def test_query_endpoint_validates_request(client):
    response = await client.post("/query", json={"bad": "data"})
    assert response.status_code == 422
