import pytest
from unittest.mock import patch

K8S_PATCH = "app.api.v1.quotas.K8sService"


@pytest.mark.asyncio
async def test_list_resource_quotas_empty(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_resource_quotas.return_value = []
        r = await client.get("/api/v1/quotas/resourcequotas", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_resource_quotas_returns_data(client, auth_headers):
    mock_quota = {
        "name": "compute-resources",
        "namespace": "pi-apps",
        "resources": [
            {"resource": "cpu", "hard": "4", "used": "1"},
            {"resource": "memory", "hard": "8Gi", "used": "2Gi"},
        ],
        "created_at": None,
    }
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_resource_quotas.return_value = [mock_quota]
        r = await client.get("/api/v1/quotas/resourcequotas", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "compute-resources"
    assert r.json()[0]["resources"][0]["resource"] == "cpu"


@pytest.mark.asyncio
async def test_list_limit_ranges_empty(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_limit_ranges.return_value = []
        r = await client.get("/api/v1/quotas/limitranges", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_limit_ranges_returns_data(client, auth_headers):
    mock_lr = {
        "name": "default-limits",
        "namespace": "pi-apps",
        "limits": [
            {
                "type": "Container",
                "resource": "cpu",
                "max": "2",
                "min": None,
                "default": "200m",
                "default_request": "100m",
            }
        ],
        "created_at": None,
    }
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_limit_ranges.return_value = [mock_lr]
        r = await client.get("/api/v1/quotas/limitranges", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()[0]["name"] == "default-limits"
    assert r.json()[0]["limits"][0]["type"] == "Container"


@pytest.mark.asyncio
async def test_list_resource_quotas_no_auth(client):
    r = await client.get("/api/v1/quotas/resourcequotas")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_limit_ranges_no_auth(client):
    r = await client.get("/api/v1/quotas/limitranges")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_resource_quotas_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/quotas/resourcequotas", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_list_limit_ranges_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/quotas/limitranges", headers=viewer_headers)
    assert r.status_code == 403
