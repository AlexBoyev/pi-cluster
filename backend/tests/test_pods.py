import pytest
from unittest.mock import patch

MOCK_POD = {
    "name": "my-app-abc-123",
    "namespace": "pi-apps",
    "phase": "Running",
    "node": "pi-node2",
    "pod_ip": "10.42.1.5",
    "containers": ["my-app"],
}

MOCK_POD_DETAIL = {
    "name": "my-app-abc-123",
    "namespace": "pi-apps",
    "phase": "Running",
    "node": "pi-node2",
    "pod_ip": "10.42.1.5",
    "qos_class": "BestEffort",
    "start_time": "2026-01-01T00:00:00",
    "containers": [],
    "conditions": [],
    "events": [],
}

K8S_PATCH = "app.api.v1.pods.K8sService"


@pytest.mark.asyncio
async def test_list_pods_empty(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_pods_in_namespace.return_value = []
        r = await client.get("/api/v1/pods/?namespace=pi-apps", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_pods_returns_data(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_pods_in_namespace.return_value = [MOCK_POD]
        r = await client.get("/api/v1/pods/?namespace=pi-apps", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "my-app-abc-123"
    assert data[0]["phase"] == "Running"


@pytest.mark.asyncio
async def test_get_pod_detail(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_pod_detail.return_value = MOCK_POD_DETAIL
        r = await client.get("/api/v1/pods/pi-apps/my-app-abc-123", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "my-app-abc-123"
    assert r.json()["qos_class"] == "BestEffort"


@pytest.mark.asyncio
async def test_get_pod_detail_not_found(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_pod_detail.return_value = None
        r = await client.get("/api/v1/pods/pi-apps/nonexistent", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_pods_no_auth(client):
    r = await client.get("/api/v1/pods/?namespace=pi-apps")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_pods_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/pods/?namespace=pi-apps", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_pod_detail_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/pods/pi-apps/my-app-abc-123", headers=viewer_headers)
    assert r.status_code == 403
