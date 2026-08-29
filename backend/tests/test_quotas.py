import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_list_resource_quotas(client, auth_headers):
    with patch("app.api.v1.quotas.K8sService") as MockK8s:
        MockK8s.return_value.list_resource_quotas.return_value = []
        r = await client.get("/api/v1/quotas/resourcequotas", headers=auth_headers)
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_list_limit_ranges(client, auth_headers):
    with patch("app.api.v1.quotas.K8sService") as MockK8s:
        MockK8s.return_value.list_limit_ranges.return_value = []
        r = await client.get("/api/v1/quotas/limitranges", headers=auth_headers)
        assert r.status_code == 200
