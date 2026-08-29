"""Tests for K8s services and ingresses endpoints."""
import pytest
from unittest.mock import patch

MOCK_SERVICE = {
    "name": "my-app",
    "namespace": "pi-apps",
    "type": "ClusterIP",
    "cluster_ip": "10.43.0.100",
    "ports": [{"port": 80, "target_port": 8080, "protocol": "TCP"}],
    "selector": {"app": "my-app"},
    "created_at": "2026-01-01T00:00:00Z",
}

MOCK_INGRESS = {
    "name": "my-app",
    "namespace": "pi-apps",
    "rules": [{"host": "my-app.pi-cluster.local", "paths": [{"path": "/", "service": "my-app", "port": 80}]}],
    "tls": [],
    "created_at": "2026-01-01T00:00:00Z",
}

K8S_PATCH = "app.api.v1.services.K8sService"


@pytest.mark.asyncio
async def test_list_services_empty(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_services.return_value = []
        r = await client.get("/api/v1/services", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_services_returns_data(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_services.return_value = [MOCK_SERVICE]
        r = await client.get("/api/v1/services", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "my-app"


@pytest.mark.asyncio
async def test_list_services_filter_namespace(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_services.return_value = []
        r = await client.get("/api/v1/services?namespace=pi-apps", headers=auth_headers)
    assert r.status_code == 200
    MockK8s.return_value.list_services.assert_called_once_with("pi-apps")


@pytest.mark.asyncio
async def test_list_ingresses_empty(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_ingresses.return_value = []
        r = await client.get("/api/v1/ingresses", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_ingresses_returns_data(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_ingresses.return_value = [MOCK_INGRESS]
        r = await client.get("/api/v1/ingresses", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "my-app"


@pytest.mark.asyncio
async def test_list_services_no_auth(client):
    r = await client.get("/api/v1/services")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_ingresses_no_auth(client):
    r = await client.get("/api/v1/ingresses")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_services_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/services", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_list_ingresses_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/ingresses", headers=viewer_headers)
    assert r.status_code == 403
