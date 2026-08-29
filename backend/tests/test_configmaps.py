import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_list_configmaps(client, auth_headers):
    with patch("app.api.v1.configmaps.K8sService") as MockK8s:
        MockK8s.return_value.list_configmaps.return_value = []
        r = await client.get("/api/v1/configmaps/", headers=auth_headers)
        assert r.status_code == 200
