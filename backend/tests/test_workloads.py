"""Comprehensive workload lifecycle, validation, and permission tests."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# K8sService is imported and instantiated in the workloads router via get_service().
# All mocking must target this location so the injected instance is the mock.
K8S_PATCH = "app.api.v1.workloads.K8sService"
K8S_SERVICE_PATCH = "app.api.v1.workloads.K8sService"

# A fully-populated mock workload response that satisfies WorkloadResponse validation.
MOCK_WORKLOAD_RESPONSE = {
    "id": 1,
    "name": "test-app",
    "namespace": "pi-apps",
    "image": "nginx:alpine",
    "replicas": 1,
    "ready_replicas": 1,
    "status": "running",
    "target_node": None,
    "ingress_host": None,
    "container_port": None,
    "cpu_limit": "500m",
    "memory_limit": "256Mi",
    "liveness_path": None,
    "readiness_path": None,
    "env_vars": {},
    "created_at": "2024-01-01T00:00:00",
}

VALID_CREATE_BODY = {
    "name": "test-app",
    "image": "nginx:alpine",
    "replicas": 1,
}


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_workloads_returns_list(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_workloads.return_value = []
        MockK8s.return_value.get_ready_replicas.return_value = 0
        r = await client.get("/api/v1/workloads/", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_list_workloads_requires_auth(client):
    """Workloads router has get_current_user applied at the router level."""
    r = await client.get("/api/v1/workloads/")
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# CAPACITY
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_capacity_returns_list(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_node_capacities.return_value = []
        r = await client.get("/api/v1/workloads/capacity", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# CREATE — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_workload_success(client, auth_headers):
    with patch(K8S_SERVICE_PATCH) as MockK8s:
        instance = MockK8s.return_value
        instance.create_deployment.return_value = None
        instance.pick_best_node.return_value = "pi-node1"
        instance.get_ready_replicas.return_value = 0

        r = await client.post("/api/v1/workloads/", headers=auth_headers, json={
            "name": "ci-workload",
            "image": "nginx:alpine",
            "replicas": 2,
        })

    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "ci-workload"
    assert data["image"] == "nginx:alpine"
    assert data["replicas"] == 2
    assert "id" in data
    assert "status" in data

    # Clean up: delete the workload record so it doesn't pollute other tests
    with patch(K8S_SERVICE_PATCH) as MockK8s:
        instance = MockK8s.return_value
        instance.delete_deployment.return_value = None
        await client.delete("/api/v1/workloads/ci-workload", headers=auth_headers)


# ---------------------------------------------------------------------------
# CREATE — input validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_workload_invalid_name_spaces(client, auth_headers):
    r = await client.post("/api/v1/workloads/", headers=auth_headers, json={
        "name": "bad name",
        "image": "nginx:alpine",
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_workload_invalid_name_uppercase(client, auth_headers):
    r = await client.post("/api/v1/workloads/", headers=auth_headers, json={
        "name": "BadName",
        "image": "nginx:alpine",
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_workload_replicas_zero(client, auth_headers):
    r = await client.post("/api/v1/workloads/", headers=auth_headers, json={
        "name": "test-app",
        "image": "nginx:alpine",
        "replicas": 0,
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_workload_replicas_too_high(client, auth_headers):
    r = await client.post("/api/v1/workloads/", headers=auth_headers, json={
        "name": "test-app",
        "image": "nginx:alpine",
        "replicas": 11,
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_workload_missing_image(client, auth_headers):
    r = await client.post("/api/v1/workloads/", headers=auth_headers, json={
        "name": "test-app",
    })
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# CREATE — permission enforcement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_workload_requires_auth(client):
    r = await client.post("/api/v1/workloads/", json=VALID_CREATE_BODY)
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_workload_viewer_forbidden(client, viewer_headers):
    r = await client.post("/api/v1/workloads/", headers=viewer_headers, json=VALID_CREATE_BODY)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Helper: create a workload for mutation tests
# ---------------------------------------------------------------------------

async def _create_test_workload(client, auth_headers, name: str = "mutation-app") -> dict:
    with patch(K8S_SERVICE_PATCH) as MockK8s:
        instance = MockK8s.return_value
        instance.create_deployment.return_value = None
        instance.pick_best_node.return_value = "pi-node1"
        instance.get_ready_replicas.return_value = 0
        r = await client.post("/api/v1/workloads/", headers=auth_headers, json={
            "name": name,
            "image": "nginx:alpine",
            "replicas": 1,
        })
    assert r.status_code == 201, r.text
    return r.json()


async def _delete_test_workload(client, auth_headers, name: str) -> None:
    with patch(K8S_SERVICE_PATCH) as MockK8s:
        MockK8s.return_value.delete_deployment.return_value = None
        await client.delete(f"/api/v1/workloads/{name}", headers=auth_headers)


# ---------------------------------------------------------------------------
# SCALE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scale_workload_success(client, auth_headers):
    await _create_test_workload(client, auth_headers, "scale-app")
    try:
        with patch(K8S_SERVICE_PATCH) as MockK8s:
            MockK8s.return_value.scale_deployment.return_value = None
            r = await client.patch("/api/v1/workloads/scale-app/scale", headers=auth_headers,
                                   json={"replicas": 3})
        assert r.status_code == 200
        assert r.json()["replicas"] == 3
    finally:
        await _delete_test_workload(client, auth_headers, "scale-app")


@pytest.mark.asyncio
async def test_scale_workload_replicas_zero_rejected(client, auth_headers):
    r = await client.patch("/api/v1/workloads/any-app/scale", headers=auth_headers,
                           json={"replicas": 0})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_scale_workload_replicas_too_high_rejected(client, auth_headers):
    r = await client.patch("/api/v1/workloads/any-app/scale", headers=auth_headers,
                           json={"replicas": 11})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_scale_workload_requires_admin(client, viewer_headers):
    r = await client.patch("/api/v1/workloads/any-app/scale", headers=viewer_headers,
                           json={"replicas": 2})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_scale_workload_requires_auth(client):
    r = await client.patch("/api/v1/workloads/any-app/scale", json={"replicas": 2})
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# IMAGE UPDATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_image_success(client, auth_headers):
    await _create_test_workload(client, auth_headers, "image-app")
    try:
        with patch(K8S_SERVICE_PATCH) as MockK8s:
            MockK8s.return_value.update_deployment_image.return_value = None
            r = await client.patch("/api/v1/workloads/image-app/image", headers=auth_headers,
                                   json={"image": "nginx:1.25"})
        assert r.status_code == 200
        assert r.json()["image"] == "nginx:1.25"
    finally:
        await _delete_test_workload(client, auth_headers, "image-app")


@pytest.mark.asyncio
async def test_update_image_requires_admin(client, viewer_headers):
    r = await client.patch("/api/v1/workloads/any-app/image", headers=viewer_headers,
                           json={"image": "nginx:latest"})
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# ENV UPDATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_env_success(client, auth_headers):
    await _create_test_workload(client, auth_headers, "env-app")
    try:
        with patch(K8S_SERVICE_PATCH) as MockK8s:
            MockK8s.return_value.update_deployment_env.return_value = None
            r = await client.patch("/api/v1/workloads/env-app/env", headers=auth_headers,
                                   json={"env_vars": {"MY_VAR": "hello"}})
        assert r.status_code == 200
    finally:
        await _delete_test_workload(client, auth_headers, "env-app")


@pytest.mark.asyncio
async def test_update_env_requires_admin(client, viewer_headers):
    r = await client.patch("/api/v1/workloads/any-app/env", headers=viewer_headers,
                           json={"env_vars": {}})
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# RESOURCE UPDATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_resources_success(client, auth_headers):
    await _create_test_workload(client, auth_headers, "resources-app")
    try:
        with patch(K8S_SERVICE_PATCH) as MockK8s:
            MockK8s.return_value.update_deployment_resources.return_value = None
            r = await client.patch("/api/v1/workloads/resources-app/resources", headers=auth_headers,
                                   json={"cpu_limit": "1000m", "memory_limit": "512Mi"})
        assert r.status_code == 200
        data = r.json()
        assert data["cpu_limit"] == "1000m"
        assert data["memory_limit"] == "512Mi"
    finally:
        await _delete_test_workload(client, auth_headers, "resources-app")


@pytest.mark.asyncio
async def test_update_resources_requires_admin(client, viewer_headers):
    r = await client.patch("/api/v1/workloads/any-app/resources", headers=viewer_headers,
                           json={"cpu_limit": "500m", "memory_limit": "256Mi"})
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# PROBES UPDATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_probes_no_port_is_ok(client, auth_headers):
    """Clearing probes (None paths) on a workload without a port is valid."""
    await _create_test_workload(client, auth_headers, "probes-app")
    try:
        with patch(K8S_SERVICE_PATCH) as MockK8s:
            MockK8s.return_value.update_deployment_probes.return_value = None
            r = await client.patch("/api/v1/workloads/probes-app/probes", headers=auth_headers,
                                   json={"liveness_path": None, "readiness_path": None})
        assert r.status_code == 200
    finally:
        await _delete_test_workload(client, auth_headers, "probes-app")


@pytest.mark.asyncio
async def test_update_probes_requires_admin(client, viewer_headers):
    r = await client.patch("/api/v1/workloads/any-app/probes", headers=viewer_headers,
                           json={"liveness_path": "/health", "readiness_path": "/ready"})
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# ROLLING RESTART
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rolling_restart_success(client, auth_headers):
    await _create_test_workload(client, auth_headers, "restart-app")
    try:
        with patch(K8S_SERVICE_PATCH) as MockK8s:
            MockK8s.return_value.restart_deployment.return_value = None
            r = await client.post("/api/v1/workloads/restart-app/restart", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["restarted"] == "restart-app"
    finally:
        await _delete_test_workload(client, auth_headers, "restart-app")


@pytest.mark.asyncio
async def test_rolling_restart_requires_admin(client, viewer_headers):
    r = await client.post("/api/v1/workloads/any-app/restart", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_rolling_restart_requires_auth(client):
    r = await client.post("/api/v1/workloads/any-app/restart")
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET PODS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_pods_success(client, auth_headers):
    await _create_test_workload(client, auth_headers, "pods-app")
    try:
        with patch(K8S_SERVICE_PATCH) as MockK8s:
            MockK8s.return_value.get_pod_list.return_value = []
            r = await client.get("/api/v1/workloads/pods-app/pods", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
    finally:
        await _delete_test_workload(client, auth_headers, "pods-app")


@pytest.mark.asyncio
async def test_get_pods_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/workloads/nonexistent/pods", headers=viewer_headers)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_workload_success(client, auth_headers):
    await _create_test_workload(client, auth_headers, "delete-me")
    with patch(K8S_SERVICE_PATCH) as MockK8s:
        MockK8s.return_value.delete_deployment.return_value = None
        r = await client.delete("/api/v1/workloads/delete-me", headers=auth_headers)
    # The router returns dict with status 200, not 204
    assert r.status_code in (200, 204)


@pytest.mark.asyncio
async def test_delete_workload_requires_admin(client, viewer_headers):
    r = await client.delete("/api/v1/workloads/any-app", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_delete_workload_requires_auth(client):
    r = await client.delete("/api/v1/workloads/any-app")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_delete_nonexistent_workload_returns_404(client, auth_headers):
    with patch(K8S_SERVICE_PATCH) as MockK8s:
        MockK8s.return_value.delete_deployment.return_value = None
        r = await client.delete("/api/v1/workloads/no-such-workload-xyz", headers=auth_headers)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Viewer read-only access
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_viewer_can_list_workloads(client, viewer_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_ready_replicas.return_value = 0
        r = await client.get("/api/v1/workloads/", headers=viewer_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_viewer_cannot_create_workload(client, viewer_headers):
    r = await client.post("/api/v1/workloads/", headers=viewer_headers, json=VALID_CREATE_BODY)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_delete_workload(client, viewer_headers):
    r = await client.delete("/api/v1/workloads/any-app", headers=viewer_headers)
    assert r.status_code == 403
