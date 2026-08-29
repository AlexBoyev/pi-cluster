import pytest
from unittest.mock import patch

MOCK_EVENT = {
    "namespace": "pi-apps",
    "type": "Normal",
    "reason": "Pulled",
    "message": "Successfully pulled image",
    "object_kind": "Pod",
    "object_name": "my-app-pod",
    "count": 1,
    "first_time": None,
    "last_time": None,
}

K8S_PATCH = "app.api.v1.events.K8sService"


@pytest.mark.asyncio
async def test_list_events_empty(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_cluster_events.return_value = []
        r = await client.get("/api/v1/events/", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_events_returns_data(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_cluster_events.return_value = [MOCK_EVENT]
        r = await client.get("/api/v1/events/", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["namespace"] == "pi-apps"
    assert data[0]["reason"] == "Pulled"
    assert data[0]["type"] == "Normal"


@pytest.mark.asyncio
async def test_list_events_filter_namespace(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_cluster_events.return_value = []
        r = await client.get("/api/v1/events/?namespace=pi-apps", headers=auth_headers)
    assert r.status_code == 200
    MockK8s.return_value.get_cluster_events.assert_called_once_with("pi-apps", None, 200)


@pytest.mark.asyncio
async def test_list_events_filter_type(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_cluster_events.return_value = []
        r = await client.get("/api/v1/events/?event_type=Warning", headers=auth_headers)
    assert r.status_code == 200
    MockK8s.return_value.get_cluster_events.assert_called_once_with(None, "Warning", 200)


@pytest.mark.asyncio
async def test_list_events_custom_limit(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_cluster_events.return_value = []
        r = await client.get("/api/v1/events/?limit=50", headers=auth_headers)
    assert r.status_code == 200
    MockK8s.return_value.get_cluster_events.assert_called_once_with(None, None, 50)


@pytest.mark.asyncio
async def test_list_events_invalid_limit(client, auth_headers):
    r = await client.get("/api/v1/events/?limit=0", headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_events_no_auth(client):
    r = await client.get("/api/v1/events/")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_events_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/events/", headers=viewer_headers)
    assert r.status_code == 403
