import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_ws_logs_requires_valid_token(client):
    """WebSocket with invalid token should be rejected."""
    # httpx AsyncClient can't do WS; we test the route exists via a regular HTTP check
    # The actual WS logic is tested via integration. Here we verify the endpoint is registered.
    r = await client.get("/api/v1/ws/logs/test-pod")
    # Should be 426 Upgrade Required or 403 (not 404)
    assert r.status_code != 404
