import pytest
from unittest.mock import patch

MOCK_STATEFULSET = {
    "name": "postgres",
    "namespace": "pi-apps",
    "replicas": 1,
    "ready_replicas": 1,
    "image": "postgres:16",
    "created_at": "2026-01-01T00:00:00Z",
}

MOCK_DAEMONSET = {
    "name": "node-exporter",
    "namespace": "monitoring",
    "desired": 4,
    "ready": 4,
    "image": "prom/node-exporter:latest",
    "created_at": "2026-01-01T00:00:00Z",
}

K8S_PATCH = "app.api.v1.objects.K8sService"


@pytest.mark.asyncio
async def test_list_statefulsets_empty(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_statefulsets.return_value = []
        r = await client.get("/api/v1/objects/statefulsets", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_statefulsets_returns_data(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_statefulsets.return_value = [MOCK_STATEFULSET]
        r = await client.get("/api/v1/objects/statefulsets", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "postgres"


@pytest.mark.asyncio
async def test_list_statefulsets_filter_namespace(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_statefulsets.return_value = []
        r = await client.get("/api/v1/objects/statefulsets?namespace=pi-apps", headers=auth_headers)
    assert r.status_code == 200
    MockK8s.return_value.list_statefulsets.assert_called_once_with("pi-apps")


@pytest.mark.asyncio
async def test_list_daemonsets_empty(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_daemonsets.return_value = []
        r = await client.get("/api/v1/objects/daemonsets", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_daemonsets_returns_data(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_daemonsets.return_value = [MOCK_DAEMONSET]
        r = await client.get("/api/v1/objects/daemonsets", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "node-exporter"
    assert data[0]["desired"] == 4


@pytest.mark.asyncio
async def test_list_statefulsets_no_auth(client):
    r = await client.get("/api/v1/objects/statefulsets")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_daemonsets_no_auth(client):
    r = await client.get("/api/v1/objects/daemonsets")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_statefulsets_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/objects/statefulsets", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_list_daemonsets_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/objects/daemonsets", headers=viewer_headers)
    assert r.status_code == 403
