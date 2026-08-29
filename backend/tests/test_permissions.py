"""
Comprehensive permission matrix tests.

Verifies that:
- Viewers are blocked from ALL cluster/infrastructure endpoints (GET and write)
- Unauthenticated requests to protected routes get 401 or 403
- Admins can perform all operations
"""
import pytest
from unittest.mock import patch, AsyncMock

K8S_WORKLOADS = "app.api.v1.workloads.K8sService"
K8S_STORAGE = "app.api.v1.storage.K8sService"
K8S_NAMESPACES = "app.api.v1.namespaces.K8sService"
K8S_CONFIGMAPS = "app.api.v1.configmaps.K8sService"
K8S_SECRETS = "app.api.v1.secrets.K8sService"
SSH_PATCH = "app.services.ssh_service.ssh_service.exec_command"


# ===========================================================================
# VIEWER — forbidden from ALL cluster/infrastructure endpoints
# ===========================================================================

@pytest.mark.asyncio
async def test_viewer_cannot_create_workload(client, viewer_headers):
    r = await client.post("/api/v1/workloads/", headers=viewer_headers,
                          json={"name": "x", "image": "nginx"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_delete_workload(client, viewer_headers):
    r = await client.delete("/api/v1/workloads/any-app", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_scale_workload(client, viewer_headers):
    r = await client.patch("/api/v1/workloads/any-app/scale", headers=viewer_headers,
                           json={"replicas": 2})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_create_namespace(client, viewer_headers):
    r = await client.post("/api/v1/namespaces/", headers=viewer_headers,
                          json={"name": "new-ns"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_delete_namespace(client, viewer_headers):
    r = await client.delete("/api/v1/namespaces/some-ns", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_restart_node(client, viewer_headers):
    r = await client.post("/api/v1/nodes/1/restart", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_shutdown_node(client, viewer_headers):
    r = await client.post("/api/v1/nodes/1/shutdown", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_create_user(client, viewer_headers):
    r = await client.post("/api/v1/users/", headers=viewer_headers,
                          json={"username": "hacker", "password": "Password1!", "role": "viewer"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_list_users(client, viewer_headers):
    r = await client.get("/api/v1/users/", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_delete_user(client, viewer_headers):
    r = await client.delete("/api/v1/users/1", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_create_pvc(client, viewer_headers):
    r = await client.post("/api/v1/storage/pvcs", headers=viewer_headers,
                          json={"name": "pvc", "namespace": "pi-apps",
                                "storage_class": "local-path", "size": "1Gi"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_delete_pvc(client, viewer_headers):
    r = await client.delete("/api/v1/storage/pvcs/pi-apps/some-pvc", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_create_configmap(client, viewer_headers):
    r = await client.post("/api/v1/configmaps/", headers=viewer_headers,
                          json={"name": "my-cm", "namespace": "pi-apps", "data": {}})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_delete_configmap(client, viewer_headers):
    r = await client.delete("/api/v1/configmaps/my-cm", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_list_secrets(client, viewer_headers):
    r = await client.get("/api/v1/secrets/", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_create_secret(client, viewer_headers):
    r = await client.post("/api/v1/secrets/", headers=viewer_headers,
                          json={"name": "my-secret", "namespace": "pi-apps", "data": {}})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_delete_secret(client, viewer_headers):
    r = await client.delete("/api/v1/secrets/my-secret", headers=viewer_headers)
    assert r.status_code == 403


# ===========================================================================
# NO TOKEN — all protected routes must return 401 or 403
# ===========================================================================

@pytest.mark.asyncio
async def test_no_token_workload_create(client):
    r = await client.post("/api/v1/workloads/", json={"name": "x", "image": "nginx"})
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_no_token_workload_delete(client):
    r = await client.delete("/api/v1/workloads/any-app")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_no_token_namespace_create(client):
    r = await client.post("/api/v1/namespaces/", json={"name": "new-ns"})
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_no_token_namespace_delete(client):
    r = await client.delete("/api/v1/namespaces/some-ns")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_no_token_node_restart(client):
    r = await client.post("/api/v1/nodes/1/restart")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_no_token_user_list(client):
    r = await client.get("/api/v1/users/")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_no_token_user_create(client):
    r = await client.post("/api/v1/users/",
                          json={"username": "x", "password": "Password1!", "role": "viewer"})
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_no_token_pvc_create(client):
    r = await client.post("/api/v1/storage/pvcs",
                          json={"name": "p", "namespace": "pi-apps",
                                "storage_class": "local-path", "size": "1Gi"})
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_no_token_pvc_delete(client):
    r = await client.delete("/api/v1/storage/pvcs/pi-apps/pvc")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_no_token_configmap_create(client):
    r = await client.post("/api/v1/configmaps/",
                          json={"name": "cm", "namespace": "pi-apps", "data": {}})
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_no_token_secret_list(client):
    r = await client.get("/api/v1/secrets/")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_no_token_secret_create(client):
    r = await client.post("/api/v1/secrets/",
                          json={"name": "s", "namespace": "pi-apps", "data": {}})
    assert r.status_code in (401, 403)


# ===========================================================================
# ADMIN — can perform all operations (spot checks)
# ===========================================================================

@pytest.mark.asyncio
async def test_admin_can_list_workloads(client, auth_headers):
    with patch(K8S_WORKLOADS) as MockK8s:
        MockK8s.return_value.get_ready_replicas.return_value = 0
        r = await client.get("/api/v1/workloads/", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_can_list_users(client, auth_headers):
    r = await client.get("/api/v1/users/", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_can_list_secrets(client, auth_headers):
    with patch(K8S_SECRETS) as MockK8s:
        MockK8s.return_value.list_secrets.return_value = []
        r = await client.get("/api/v1/secrets/", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_can_create_and_delete_namespace(client, auth_headers):
    new_ns = {"name": "perm-test-ns", "status": "Active", "created_at": None, "labels": {}}
    with patch(K8S_NAMESPACES) as MockK8s:
        MockK8s.return_value.create_namespace.return_value = None
        MockK8s.return_value.list_namespaces.return_value = [new_ns]
        r = await client.post("/api/v1/namespaces/", headers=auth_headers,
                              json={"name": "perm-test-ns"})
    assert r.status_code == 201

    with patch(K8S_NAMESPACES) as MockK8s:
        MockK8s.return_value.delete_namespace.return_value = None
        r = await client.delete("/api/v1/namespaces/perm-test-ns", headers=auth_headers)
    assert r.status_code == 204
