import pytest
from unittest.mock import patch, AsyncMock

MOCK_CAPACITY = {
    "cpu_allocatable_cores": 16.0,
    "cpu_requested_cores": 4.0,
    "cpu_used_cores": 2.0,
    "memory_allocatable_bytes": 8_000_000_000,
    "memory_requested_bytes": 2_000_000_000,
    "memory_used_bytes": 1_500_000_000,
    "nodes": [
        {
            "node_name": "pi-node1",
            "cpu_allocatable_cores": 4.0,
            "cpu_requested_cores": 1.0,
            "cpu_used_cores": 0.5,
            "memory_allocatable_bytes": 2_000_000_000,
            "memory_requested_bytes": 500_000_000,
            "memory_used_bytes": 400_000_000,
            "ready": True,
            "schedulable": True,
        }
    ],
}

CAPACITY_PATCH = "app.api.v1.cluster.get_cluster_capacity"


@pytest.mark.asyncio
async def test_cluster_capacity(client, auth_headers):
    from app.schemas.cluster import ClusterCapacity
    with patch(CAPACITY_PATCH, new_callable=AsyncMock) as mock_cap:
        mock_cap.return_value = ClusterCapacity(**MOCK_CAPACITY)
        r = await client.get("/api/v1/cluster/capacity", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["cpu_allocatable_cores"] == 16.0
    assert isinstance(data["nodes"], list)
    assert len(data["nodes"]) == 1
    assert data["nodes"][0]["node_name"] == "pi-node1"
    assert data["nodes"][0]["ready"] is True


@pytest.mark.asyncio
async def test_cluster_capacity_no_auth(client):
    r = await client.get("/api/v1/cluster/capacity")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_cluster_capacity_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/cluster/capacity", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_cluster_capacity_k8s_unreachable(client, auth_headers):
    from fastapi import HTTPException
    with patch(CAPACITY_PATCH, new_callable=AsyncMock) as mock_cap:
        mock_cap.side_effect = HTTPException(status_code=503, detail="Kubernetes API is unreachable")
        r = await client.get("/api/v1/cluster/capacity", headers=auth_headers)
    assert r.status_code == 503
