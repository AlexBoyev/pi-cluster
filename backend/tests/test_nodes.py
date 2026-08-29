import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_list_nodes(client, auth_headers):
    r = await client.get("/api/v1/nodes/", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_register_node(client, auth_headers):
    r = await client.post("/api/v1/nodes/", headers=auth_headers, json={
        "name": "test-node-ci",
        "ip_address": "10.100.102.99",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "test-node-ci"
    assert data["ip_address"] == "10.100.102.99"
    return data["id"]


@pytest.mark.asyncio
async def test_get_node(client, auth_headers):
    # Register first
    r = await client.post("/api/v1/nodes/", headers=auth_headers, json={
        "name": "test-node-get",
        "ip_address": "10.100.102.98",
    })
    node_id = r.json()["id"]
    r2 = await client.get(f"/api/v1/nodes/{node_id}", headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()["id"] == node_id


@pytest.mark.asyncio
async def test_get_node_not_found(client, auth_headers):
    r = await client.get("/api/v1/nodes/999999", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_restart_node(client, auth_headers):
    r = await client.post("/api/v1/nodes/", headers=auth_headers, json={
        "name": "test-node-restart",
        "ip_address": "10.100.102.97",
    })
    node_id = r.json()["id"]
    with patch("app.services.ssh_service.ssh_service.exec_command", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = ""
        r2 = await client.post(f"/api/v1/nodes/{node_id}/restart", headers=auth_headers)
        assert r2.status_code == 202
        assert r2.json()["status"] == "restarting"
        mock_exec.assert_awaited_once()


@pytest.mark.asyncio
async def test_shutdown_node(client, auth_headers):
    r = await client.post("/api/v1/nodes/", headers=auth_headers, json={
        "name": "test-node-shutdown",
        "ip_address": "10.100.102.96",
    })
    node_id = r.json()["id"]
    with patch("app.services.ssh_service.ssh_service.exec_command", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = ""
        r2 = await client.post(f"/api/v1/nodes/{node_id}/shutdown", headers=auth_headers)
        assert r2.status_code == 202
        assert r2.json()["status"] == "shutting_down"
        mock_exec.assert_awaited_once()
