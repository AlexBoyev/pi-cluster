import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone


MOCK_ENTRY = {
    "id": 1,
    "alert_name": "NodeDown",
    "severity": "critical",
    "node_name": "pi-node2",
    "instance": "10.100.102.16:9100",
    "summary": "Node is down",
    "fired_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    "resolved_at": datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc),
}

REPO_PATCH = "app.api.v1.alert_history.AlertHistoryRepository"


@pytest.mark.asyncio
async def test_list_alert_history_empty(client, auth_headers):
    with patch(REPO_PATCH) as MockRepo:
        MockRepo.return_value.get_recent = AsyncMock(return_value=[])
        r = await client.get("/api/v1/alert-history/", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_alert_history_returns_entries(client, auth_headers):
    from app.schemas.alert_history import AlertHistoryEntry
    entry = AlertHistoryEntry(**MOCK_ENTRY)
    with patch(REPO_PATCH) as MockRepo:
        MockRepo.return_value.get_recent = AsyncMock(return_value=[entry])
        r = await client.get("/api/v1/alert-history/", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["alert_name"] == "NodeDown"
    assert data[0]["severity"] == "critical"
    assert data[0]["node_name"] == "pi-node2"


@pytest.mark.asyncio
async def test_list_alert_history_pagination(client, auth_headers):
    with patch(REPO_PATCH) as MockRepo:
        MockRepo.return_value.get_recent = AsyncMock(return_value=[])
        r = await client.get("/api/v1/alert-history/?limit=10&offset=5", headers=auth_headers)
    assert r.status_code == 200
    MockRepo.return_value.get_recent.assert_called_once_with(
        limit=10, offset=5, severity=None, state=None
    )


@pytest.mark.asyncio
async def test_list_alert_history_filter_severity(client, auth_headers):
    with patch(REPO_PATCH) as MockRepo:
        MockRepo.return_value.get_recent = AsyncMock(return_value=[])
        r = await client.get("/api/v1/alert-history/?severity=critical", headers=auth_headers)
    assert r.status_code == 200
    MockRepo.return_value.get_recent.assert_called_once_with(
        limit=100, offset=0, severity="critical", state=None
    )


@pytest.mark.asyncio
async def test_list_alert_history_filter_state(client, auth_headers):
    with patch(REPO_PATCH) as MockRepo:
        MockRepo.return_value.get_recent = AsyncMock(return_value=[])
        r = await client.get("/api/v1/alert-history/?state=resolved", headers=auth_headers)
    assert r.status_code == 200
    MockRepo.return_value.get_recent.assert_called_once_with(
        limit=100, offset=0, severity=None, state="resolved"
    )


@pytest.mark.asyncio
async def test_list_alert_history_invalid_limit(client, auth_headers):
    r = await client.get("/api/v1/alert-history/?limit=0", headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_alert_history_limit_too_large(client, auth_headers):
    r = await client.get("/api/v1/alert-history/?limit=9999", headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_alert_history_no_auth(client):
    r = await client.get("/api/v1/alert-history/")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_alert_history_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/alert-history/", headers=viewer_headers)
    assert r.status_code == 403
