import pytest
from unittest.mock import patch

NS_MOCK = [{"name": "pi-apps", "status": "Active", "created_at": None, "labels": {}}]


@pytest.mark.asyncio
async def test_list_namespaces(client, auth_headers):
    with patch("app.api.v1.namespaces.K8sService") as MockK8s:
        MockK8s.return_value.list_namespaces.return_value = NS_MOCK
        r = await client.get("/api/v1/namespaces/", headers=auth_headers)
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_create_namespace_protected(client, auth_headers):
    r = await client.post("/api/v1/namespaces/", headers=auth_headers,
                          json={"name": "kube-system"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_delete_namespace_protected(client, auth_headers):
    r = await client.delete("/api/v1/namespaces/default", headers=auth_headers)
    assert r.status_code == 400
