import pytest
from unittest.mock import patch
from datetime import datetime, timezone

MOCK_CRONJOB = {
    "name": "cleanup-job",
    "namespace": "pi-apps",
    "schedule": "0 2 * * *",
    "suspended": False,
    "active_jobs": 0,
    "last_schedule_time": None,
    "image": "busybox:latest",
    "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
}

K8S_PATCH = "app.api.v1.cronjobs.K8sService"


@pytest.mark.asyncio
async def test_list_cronjobs_empty(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_cronjobs.return_value = []
        r = await client.get("/api/v1/cronjobs/", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_cronjobs_returns_data(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_cronjobs.return_value = [MOCK_CRONJOB]
        r = await client.get("/api/v1/cronjobs/", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "cleanup-job"
    assert data[0]["schedule"] == "0 2 * * *"


@pytest.mark.asyncio
async def test_create_cronjob(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.create_cronjob.return_value = None
        MockK8s.return_value.list_cronjobs.return_value = [MOCK_CRONJOB]
        r = await client.post("/api/v1/cronjobs/", headers=auth_headers, json={
            "name": "cleanup-job",
            "namespace": "pi-apps",
            "schedule": "0 2 * * *",
            "image": "busybox:latest",
        })
    assert r.status_code == 201
    assert r.json()["name"] == "cleanup-job"


@pytest.mark.asyncio
async def test_create_cronjob_invalid_name(client, auth_headers):
    r = await client.post("/api/v1/cronjobs/", headers=auth_headers, json={
        "name": "Invalid_Name!",
        "schedule": "0 2 * * *",
        "image": "busybox",
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_cronjob_empty_schedule(client, auth_headers):
    r = await client.post("/api/v1/cronjobs/", headers=auth_headers, json={
        "name": "my-job",
        "schedule": "",
        "image": "busybox",
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_suspend_cronjob(client, auth_headers):
    suspended = {**MOCK_CRONJOB, "suspended": True}
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.set_cronjob_suspend.return_value = None
        MockK8s.return_value.list_cronjobs.return_value = [suspended]
        r = await client.patch("/api/v1/cronjobs/cleanup-job/suspend", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["suspended"] is True


@pytest.mark.asyncio
async def test_resume_cronjob(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.set_cronjob_suspend.return_value = None
        MockK8s.return_value.list_cronjobs.return_value = [MOCK_CRONJOB]
        r = await client.patch("/api/v1/cronjobs/cleanup-job/resume", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["suspended"] is False


@pytest.mark.asyncio
async def test_suspend_cronjob_not_found(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.set_cronjob_suspend.return_value = None
        MockK8s.return_value.list_cronjobs.return_value = []
        r = await client.patch("/api/v1/cronjobs/ghost/suspend", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_cronjob_jobs(client, auth_headers):
    mock_run = {
        "name": "cleanup-job-abc123",
        "succeeded": 1,
        "failed": 0,
        "active": 0,
        "start_time": None,
        "completion_time": None,
    }
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_cronjob_jobs.return_value = [mock_run]
        r = await client.get("/api/v1/cronjobs/cleanup-job/jobs", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()[0]["name"] == "cleanup-job-abc123"


@pytest.mark.asyncio
async def test_delete_cronjob(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.delete_cronjob.return_value = None
        r = await client.delete("/api/v1/cronjobs/cleanup-job", headers=auth_headers)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_list_cronjobs_no_auth(client):
    r = await client.get("/api/v1/cronjobs/")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_cronjobs_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/cronjobs/", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_create_cronjob_viewer_forbidden(client, viewer_headers):
    r = await client.post("/api/v1/cronjobs/", headers=viewer_headers, json={
        "name": "cleanup-job", "schedule": "0 2 * * *", "image": "busybox",
    })
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_delete_cronjob_viewer_forbidden(client, viewer_headers):
    r = await client.delete("/api/v1/cronjobs/cleanup-job", headers=viewer_headers)
    assert r.status_code == 403
