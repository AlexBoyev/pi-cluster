import pytest
from unittest.mock import patch, MagicMock, AsyncMock

K8S_PATCH = "app.services.k8s_service.K8sService"

MOCK_WORKLOAD = {
    "id": 1, "name": "test-app", "namespace": "pi-apps",
    "image": "nginx:alpine", "replicas": 1, "ready_replicas": 1,
    "status": "running", "target_node": None, "ingress_host": None,
    "container_port": None, "cpu_limit": None, "memory_limit": None,
    "liveness_path": None, "readiness_path": None, "env_vars": {},
    "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00",
}


@pytest.mark.asyncio
async def test_list_workloads(client, auth_headers):
    with patch("app.api.v1.workloads.K8sService") as MockK8s:
        MockK8s.return_value.list_workloads.return_value = []
        r = await client.get("/api/v1/workloads/", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_create_workload_requires_auth(client):
    r = await client.post("/api/v1/workloads/", json={"name": "x", "image": "nginx"})
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_capacity(client, auth_headers):
    with patch("app.api.v1.workloads.K8sService") as MockK8s:
        MockK8s.return_value.get_node_capacities.return_value = []
        r = await client.get("/api/v1/workloads/capacity", headers=auth_headers)
        assert r.status_code == 200
