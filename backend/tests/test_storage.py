import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_list_pvcs(client, auth_headers):
    with patch("app.api.v1.storage.K8sService") as MockK8s:
        MockK8s.return_value.list_pvcs.return_value = []
        r = await client.get("/api/v1/storage/pvcs", headers=auth_headers)
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_list_pvs(client, auth_headers):
    with patch("app.api.v1.storage.K8sService") as MockK8s:
        MockK8s.return_value.list_pvs.return_value = []
        r = await client.get("/api/v1/storage/pvs", headers=auth_headers)
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_list_storage_classes(client, auth_headers):
    with patch("app.api.v1.storage.K8sService") as MockK8s:
        MockK8s.return_value.list_storage_classes.return_value = []
        r = await client.get("/api/v1/storage/classes", headers=auth_headers)
        assert r.status_code == 200
