import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone

MOCK_CHANNEL = {
    "id": 1,
    "name": "slack-alerts",
    "channel_type": "webhook",
    "url": "https://hooks.slack.com/services/test",
    "email_address": None,
    "min_severity": "warning",
    "enabled": True,
    "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
}

REPO_PATCH = "app.api.v1.notifications.NotificationRepository"
TEST_PATCH = "app.api.v1.notifications.test_channel"


@pytest.mark.asyncio
async def test_list_channels_empty(client, auth_headers):
    with patch(REPO_PATCH) as MockRepo:
        MockRepo.return_value.list_all = AsyncMock(return_value=[])
        r = await client.get("/api/v1/notifications/channels", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_create_channel(client, auth_headers):
    from app.schemas.notification import ChannelResponse
    ch = ChannelResponse(**MOCK_CHANNEL)
    with patch(REPO_PATCH) as MockRepo:
        MockRepo.return_value.create = AsyncMock(return_value=ch)
        r = await client.post("/api/v1/notifications/channels", headers=auth_headers, json={
            "name": "slack-alerts",
            "url": "https://hooks.slack.com/services/test",
            "enabled": True,
        })
    assert r.status_code == 201
    assert r.json()["name"] == "slack-alerts"
    assert r.json()["enabled"] is True


@pytest.mark.asyncio
async def test_update_channel(client, auth_headers):
    from app.schemas.notification import ChannelResponse
    updated = ChannelResponse(**{**MOCK_CHANNEL, "enabled": False})
    with patch(REPO_PATCH) as MockRepo:
        MockRepo.return_value.get_by_id = AsyncMock(return_value=updated)
        MockRepo.return_value.update = AsyncMock(return_value=updated)
        r = await client.patch("/api/v1/notifications/channels/1", headers=auth_headers,
                               json={"enabled": False})
    assert r.status_code == 200
    assert r.json()["enabled"] is False


@pytest.mark.asyncio
async def test_update_channel_not_found(client, auth_headers):
    with patch(REPO_PATCH) as MockRepo:
        MockRepo.return_value.get_by_id = AsyncMock(return_value=None)
        r = await client.patch("/api/v1/notifications/channels/999", headers=auth_headers,
                               json={"enabled": False})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_channel(client, auth_headers):
    from app.schemas.notification import ChannelResponse
    ch = ChannelResponse(**MOCK_CHANNEL)
    with patch(REPO_PATCH) as MockRepo:
        MockRepo.return_value.get_by_id = AsyncMock(return_value=ch)
        MockRepo.return_value.delete = AsyncMock(return_value=None)
        r = await client.delete("/api/v1/notifications/channels/1", headers=auth_headers)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_delete_channel_not_found(client, auth_headers):
    with patch(REPO_PATCH) as MockRepo:
        MockRepo.return_value.get_by_id = AsyncMock(return_value=None)
        r = await client.delete("/api/v1/notifications/channels/999", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_test_channel_success(client, auth_headers):
    from app.schemas.notification import ChannelResponse
    ch = ChannelResponse(**MOCK_CHANNEL)
    with patch(REPO_PATCH) as MockRepo, patch(TEST_PATCH, new_callable=AsyncMock) as mock_test:
        MockRepo.return_value.get_by_id = AsyncMock(return_value=ch)
        mock_test.return_value = True
        r = await client.post("/api/v1/notifications/channels/1/test", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["ok"] is True


@pytest.mark.asyncio
async def test_test_channel_failure(client, auth_headers):
    from app.schemas.notification import ChannelResponse
    ch = ChannelResponse(**MOCK_CHANNEL)
    with patch(REPO_PATCH) as MockRepo, patch(TEST_PATCH, new_callable=AsyncMock) as mock_test:
        MockRepo.return_value.get_by_id = AsyncMock(return_value=ch)
        mock_test.return_value = False
        r = await client.post("/api/v1/notifications/channels/1/test", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["ok"] is False


@pytest.mark.asyncio
async def test_test_channel_not_found(client, auth_headers):
    with patch(REPO_PATCH) as MockRepo:
        MockRepo.return_value.get_by_id = AsyncMock(return_value=None)
        r = await client.post("/api/v1/notifications/channels/999/test", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_channels_no_auth(client):
    r = await client.get("/api/v1/notifications/channels")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_channels_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/notifications/channels", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_create_channel_viewer_forbidden(client, viewer_headers):
    r = await client.post("/api/v1/notifications/channels", headers=viewer_headers,
                          json={"name": "x", "url": "https://example.com"})
    assert r.status_code == 403
