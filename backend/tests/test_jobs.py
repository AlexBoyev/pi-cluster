import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_list_jobs(client, auth_headers):
    with patch("app.api.v1.jobs.K8sService") as MockK8s:
        MockK8s.return_value.list_jobs.return_value = []
        r = await client.get("/api/v1/jobs/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
