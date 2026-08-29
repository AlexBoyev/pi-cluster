"""Namespace create/delete lifecycle, protected-namespace enforcement, and permission tests."""
import pytest
from unittest.mock import patch

K8S_PATCH = "app.api.v1.namespaces.K8sService"

NS_MOCK = [{"name": "pi-apps", "status": "Active", "created_at": None, "labels": {}}]


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_namespaces(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_namespaces.return_value = NS_MOCK
        r = await client.get("/api/v1/namespaces/", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_list_namespaces_requires_auth(client):
    """Namespaces router has get_current_user applied at the router level."""
    r = await client.get("/api/v1/namespaces/")
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# CREATE — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_namespace_success(client, auth_headers):
    new_ns = {"name": "my-new-ns", "status": "Active", "created_at": None, "labels": {}}
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.create_namespace.return_value = None
        MockK8s.return_value.list_namespaces.return_value = [new_ns]
        r = await client.post("/api/v1/namespaces/", headers=auth_headers,
                              json={"name": "my-new-ns"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "my-new-ns"
    assert data["status"] == "Active"


# ---------------------------------------------------------------------------
# CREATE — protected namespaces
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_namespace_kube_system_protected(client, auth_headers):
    r = await client.post("/api/v1/namespaces/", headers=auth_headers,
                          json={"name": "kube-system"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_namespace_default_protected(client, auth_headers):
    r = await client.post("/api/v1/namespaces/", headers=auth_headers,
                          json={"name": "default"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_namespace_kube_public_protected(client, auth_headers):
    r = await client.post("/api/v1/namespaces/", headers=auth_headers,
                          json={"name": "kube-public"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_namespace_monitoring_protected(client, auth_headers):
    r = await client.post("/api/v1/namespaces/", headers=auth_headers,
                          json={"name": "monitoring"})
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# CREATE — validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_namespace_invalid_name_rejected(client, auth_headers):
    r = await client.post("/api/v1/namespaces/", headers=auth_headers,
                          json={"name": "UPPERCASE"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# CREATE — permissions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_namespace_requires_admin(client):
    r = await client.post("/api/v1/namespaces/", json={"name": "new-ns"})
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_namespace_viewer_forbidden(client, viewer_headers):
    r = await client.post("/api/v1/namespaces/", headers=viewer_headers,
                          json={"name": "new-ns"})
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# DELETE — protected namespaces
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_namespace_default_protected(client, auth_headers):
    r = await client.delete("/api/v1/namespaces/default", headers=auth_headers)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_delete_namespace_kube_system_protected(client, auth_headers):
    r = await client.delete("/api/v1/namespaces/kube-system", headers=auth_headers)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_delete_namespace_monitoring_protected(client, auth_headers):
    r = await client.delete("/api/v1/namespaces/monitoring", headers=auth_headers)
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# DELETE — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_namespace_success(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.delete_namespace.return_value = None
        r = await client.delete("/api/v1/namespaces/my-old-ns", headers=auth_headers)
    assert r.status_code == 204


# ---------------------------------------------------------------------------
# DELETE — permissions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_namespace_requires_admin(client):
    r = await client.delete("/api/v1/namespaces/some-ns")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_delete_namespace_viewer_forbidden(client, viewer_headers):
    r = await client.delete("/api/v1/namespaces/some-ns", headers=viewer_headers)
    assert r.status_code == 403
