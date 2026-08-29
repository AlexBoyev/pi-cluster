"""Storage (PVC, PV, StorageClass) tests including create/delete and permission checks."""
import pytest
from unittest.mock import patch, MagicMock

K8S_PATCH = "app.api.v1.storage.K8sService"


# ---------------------------------------------------------------------------
# LIST StorageClasses
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_storage_classes(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_storage_classes.return_value = []
        r = await client.get("/api/v1/storage/classes", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_list_storage_classes_with_data(client, auth_headers):
    mock_class = {
        "name": "local-path",
        "provisioner": "rancher.io/local-path",
        "reclaim_policy": "Delete",
        "binding_mode": "WaitForFirstConsumer",
        "is_default": True,
        "created_at": None,
    }
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_storage_classes.return_value = [mock_class]
        r = await client.get("/api/v1/storage/classes", headers=auth_headers)
    assert r.status_code == 200
    classes = r.json()
    assert len(classes) == 1
    assert classes[0]["name"] == "local-path"


# ---------------------------------------------------------------------------
# LIST PVCs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_pvcs(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_pvcs.return_value = []
        r = await client.get("/api/v1/storage/pvcs", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_list_pvcs_with_namespace_filter(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_pvcs.return_value = []
        r = await client.get("/api/v1/storage/pvcs?namespace=pi-apps", headers=auth_headers)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# LIST PVs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_pvs(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_pvs.return_value = []
        r = await client.get("/api/v1/storage/pvs", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_list_pvs_with_data(client, auth_headers):
    mock_pv = {
        "name": "pv-test",
        "status": "Available",
        "capacity": "1Gi",
        "access_modes": ["ReadWriteOnce"],
        "storage_class": "local-path",
        "reclaim_policy": "Delete",
        "claim_namespace": None,
        "claim_name": None,
        "created_at": None,
    }
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_pvs.return_value = [mock_pv]
        r = await client.get("/api/v1/storage/pvs", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()[0]["name"] == "pv-test"


# ---------------------------------------------------------------------------
# CREATE PVC
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_pvc_success(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.create_pvc.return_value = None
        r = await client.post("/api/v1/storage/pvcs", headers=auth_headers, json={
            "name": "test-pvc",
            "namespace": "pi-apps",
            "storage_class": "local-path",
            "access_modes": ["ReadWriteOnce"],
            "size": "1Gi",
        })
    assert r.status_code == 201
    assert r.json()["name"] == "test-pvc"


@pytest.mark.asyncio
async def test_create_pvc_requires_admin(client):
    r = await client.post("/api/v1/storage/pvcs", json={
        "name": "test-pvc",
        "namespace": "pi-apps",
        "storage_class": "local-path",
        "access_modes": ["ReadWriteOnce"],
        "size": "1Gi",
    })
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_pvc_viewer_forbidden(client, viewer_headers):
    r = await client.post("/api/v1/storage/pvcs", headers=viewer_headers, json={
        "name": "test-pvc",
        "namespace": "pi-apps",
        "storage_class": "local-path",
        "access_modes": ["ReadWriteOnce"],
        "size": "1Gi",
    })
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# DELETE PVC
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_pvc_success(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.delete_pvc.return_value = None
        r = await client.delete("/api/v1/storage/pvcs/pi-apps/test-pvc", headers=auth_headers)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_delete_pvc_requires_admin(client):
    r = await client.delete("/api/v1/storage/pvcs/pi-apps/test-pvc")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_delete_pvc_viewer_forbidden(client, viewer_headers):
    r = await client.delete("/api/v1/storage/pvcs/pi-apps/test-pvc", headers=viewer_headers)
    assert r.status_code == 403
