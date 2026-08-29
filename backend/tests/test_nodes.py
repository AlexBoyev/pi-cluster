"""Node CRUD, SSH operations, bulk actions, and permission tests."""
import pytest
from unittest.mock import patch, AsyncMock

SSH_PATCH = "app.services.ssh_service.ssh_service.exec_command"


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_nodes(client, auth_headers):
    r = await client.get("/api/v1/nodes/", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# REGISTER
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_node(client, auth_headers):
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
async def test_get_node_unknown_id_returns_404(client, auth_headers):
    r = await client.get("/api/v1/nodes/888888", headers=auth_headers)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# RESTART (single node)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_restart_node(client, auth_headers):
    r = await client.post("/api/v1/nodes/", headers=auth_headers, json={
        "name": "test-node-restart",
        "ip_address": "10.100.102.97",
    })
    node_id = r.json()["id"]
    with patch(SSH_PATCH, new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = ""
        r2 = await client.post(f"/api/v1/nodes/{node_id}/restart", headers=auth_headers)
    assert r2.status_code == 202
    assert r2.json()["status"] == "restarting"
    mock_exec.assert_awaited_once()


@pytest.mark.asyncio
async def test_restart_nonexistent_node_returns_404(client, auth_headers):
    with patch(SSH_PATCH, new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = ""
        r = await client.post("/api/v1/nodes/999998/restart", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_restart_node_requires_admin(client, viewer_headers):
    r = await client.post("/api/v1/nodes/1/restart", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_restart_node_requires_auth(client):
    r = await client.post("/api/v1/nodes/1/restart")
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# SHUTDOWN (single node)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_shutdown_node(client, auth_headers):
    r = await client.post("/api/v1/nodes/", headers=auth_headers, json={
        "name": "test-node-shutdown",
        "ip_address": "10.100.102.96",
    })
    node_id = r.json()["id"]
    with patch(SSH_PATCH, new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = ""
        r2 = await client.post(f"/api/v1/nodes/{node_id}/shutdown", headers=auth_headers)
    assert r2.status_code == 202
    assert r2.json()["status"] == "shutting_down"
    mock_exec.assert_awaited_once()


@pytest.mark.asyncio
async def test_shutdown_nonexistent_node_returns_404(client, auth_headers):
    with patch(SSH_PATCH, new_callable=AsyncMock):
        r = await client.post("/api/v1/nodes/999997/shutdown", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_shutdown_node_requires_admin(client, viewer_headers):
    r = await client.post("/api/v1/nodes/1/shutdown", headers=viewer_headers)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# RESTART ALL
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_restart_all_nodes(client, auth_headers):
    # Ensure at least one node exists
    await client.post("/api/v1/nodes/", headers=auth_headers, json={
        "name": "test-node-all-restart",
        "ip_address": "10.100.102.95",
    })
    with patch(SSH_PATCH, new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = ""
        r = await client.post("/api/v1/nodes/all/restart", headers=auth_headers)
    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "restarting"
    assert "count" in data


@pytest.mark.asyncio
async def test_restart_all_nodes_requires_admin(client, viewer_headers):
    r = await client.post("/api/v1/nodes/all/restart", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_restart_all_nodes_requires_auth(client):
    r = await client.post("/api/v1/nodes/all/restart")
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# SHUTDOWN ALL
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_shutdown_all_nodes(client, auth_headers):
    await client.post("/api/v1/nodes/", headers=auth_headers, json={
        "name": "test-node-all-shutdown",
        "ip_address": "10.100.102.94",
    })
    with patch(SSH_PATCH, new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = ""
        r = await client.post("/api/v1/nodes/all/shutdown", headers=auth_headers)
    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "shutting_down"
    assert "count" in data


@pytest.mark.asyncio
async def test_shutdown_all_nodes_requires_admin(client, viewer_headers):
    r = await client.post("/api/v1/nodes/all/shutdown", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_shutdown_all_nodes_requires_auth(client):
    r = await client.post("/api/v1/nodes/all/shutdown")
    assert r.status_code in (401, 403)
