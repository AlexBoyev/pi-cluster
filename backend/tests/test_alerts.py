import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

MOCK_ALERT = {
    "name": "HighCPU",
    "severity": "warning",
    "state": "firing",
    "node_name": "pi-node1",
    "summary": "CPU is high",
    "description": "CPU has been over 85% for 5 minutes",
    "fired_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    "duration_seconds": 300,
}

ALERTS_PATCH = "app.api.v1.alerts.AlertService"


@pytest.mark.asyncio
async def test_list_alerts_empty(client, auth_headers):
    with patch(ALERTS_PATCH) as Mock:
        Mock.return_value.get_alerts = AsyncMock(return_value=[])
        r = await client.get("/api/v1/alerts/", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_alerts_returns_data(client, auth_headers):
    from app.schemas.alert import AlertResponse
    with patch(ALERTS_PATCH) as Mock:
        Mock.return_value.get_alerts = AsyncMock(return_value=[AlertResponse(**MOCK_ALERT)])
        r = await client.get("/api/v1/alerts/", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "HighCPU"
    assert data[0]["severity"] == "warning"
    assert data[0]["state"] == "firing"


@pytest.mark.asyncio
async def test_list_alerts_no_auth(client):
    r = await client.get("/api/v1/alerts/")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_alerts_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/alerts/", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_list_alerts_prometheus_down(client, auth_headers):
    from fastapi import HTTPException
    with patch(ALERTS_PATCH) as Mock:
        Mock.return_value.get_alerts = AsyncMock(side_effect=HTTPException(status_code=502, detail="Prometheus unreachable"))
        r = await client.get("/api/v1/alerts/", headers=auth_headers)
    assert r.status_code == 502
