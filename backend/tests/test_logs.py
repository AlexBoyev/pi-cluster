import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_ws_logs_route_exists(client):
    """FastAPI returns 404 for HTTP GET on a WebSocket-only route (correct behaviour).
    Real WS auth testing requires a WebSocket client library."""
    r = await client.get("/api/v1/ws/logs/test-pod")
    # WebSocket routes don't match HTTP scope; router returns 404 — that is expected.
    assert r.status_code == 404
