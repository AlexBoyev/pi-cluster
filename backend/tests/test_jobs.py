import pytest
from unittest.mock import patch

MOCK_JOB = {
    "name": "batch-import",
    "namespace": "pi-apps",
    "succeeded": 1,
    "failed": 0,
    "active": 0,
    "start_time": "2026-01-01T00:00:00Z",
    "completion_time": "2026-01-01T00:05:00Z",
    "conditions": [],
}

K8S_PATCH = "app.api.v1.jobs.K8sService"


@pytest.mark.asyncio
async def test_list_jobs_empty(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_jobs.return_value = []
        r = await client.get("/api/v1/jobs/", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_jobs_returns_data(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_jobs.return_value = [MOCK_JOB]
        r = await client.get("/api/v1/jobs/", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "batch-import"
    assert data[0]["succeeded"] == 1


@pytest.mark.asyncio
async def test_list_jobs_filter_namespace(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_jobs.return_value = []
        r = await client.get("/api/v1/jobs/?namespace=pi-apps", headers=auth_headers)
    assert r.status_code == 200
    MockK8s.return_value.list_jobs.assert_called_once_with("pi-apps")


@pytest.mark.asyncio
async def test_list_jobs_no_auth(client):
    r = await client.get("/api/v1/jobs/")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_jobs_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/jobs/", headers=viewer_headers)
    assert r.status_code == 403
