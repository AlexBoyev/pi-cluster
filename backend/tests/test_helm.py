import pytest
from unittest.mock import patch

MOCK_RELEASE = {
    "name": "traefik",
    "namespace": "kube-system",
    "chart": "traefik",
    "chart_version": "28.0.0",
    "app_version": "v3.0.0",
    "status": "deployed",
    "revision": 1,
    "description": None,
    "first_deployed": "2026-01-01T00:00:00Z",
    "last_deployed": "2026-01-01T00:00:00Z",
}

K8S_PATCH = "app.api.v1.helm.K8sService"


@pytest.mark.asyncio
async def test_list_helm_releases_empty(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_helm_releases.return_value = []
        r = await client.get("/api/v1/helm/releases", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_helm_releases_returns_data(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_helm_releases.return_value = [MOCK_RELEASE]
        r = await client.get("/api/v1/helm/releases", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "traefik"
    assert data[0]["status"] == "deployed"


@pytest.mark.asyncio
async def test_list_helm_releases_filter_namespace(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_helm_releases.return_value = []
        r = await client.get("/api/v1/helm/releases?namespace=kube-system", headers=auth_headers)
    assert r.status_code == 200
    MockK8s.return_value.list_helm_releases.assert_called_once_with("kube-system")


@pytest.mark.asyncio
async def test_list_helm_releases_no_auth(client):
    r = await client.get("/api/v1/helm/releases")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_helm_releases_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/helm/releases", headers=viewer_headers)
    assert r.status_code == 403
