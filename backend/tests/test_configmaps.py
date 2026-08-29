"""ConfigMap CRUD lifecycle, validation, and permission tests."""
import pytest
from unittest.mock import patch, MagicMock

K8S_PATCH = "app.api.v1.configmaps.K8sService"

MOCK_CM_DETAIL = {
    "name": "test-cm",
    "namespace": "pi-apps",
    "data": {"key": "value"},
    "created_at": None,
}

MOCK_CM_SUMMARY = {
    "name": "test-cm",
    "namespace": "pi-apps",
    "data_keys": ["key"],
    "created_at": None,
}


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_configmaps_returns_list(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_configmaps.return_value = []
        r = await client.get("/api/v1/configmaps/", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_list_configmaps_with_mock_data(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_configmaps.return_value = [MOCK_CM_SUMMARY]
        r = await client.get("/api/v1/configmaps/", headers=auth_headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["name"] == "test-cm"


@pytest.mark.asyncio
async def test_list_configmaps_requires_auth(client):
    r = await client.get("/api/v1/configmaps/")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_configmaps_viewer_allowed(client, viewer_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_configmaps.return_value = []
        r = await client.get("/api/v1/configmaps/", headers=viewer_headers)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_configmap_success(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_configmap.return_value = None  # does not exist yet
        MockK8s.return_value.create_configmap.return_value = None
        # Second get_configmap call (after create) returns the created object
        MockK8s.return_value.get_configmap.side_effect = [None, MOCK_CM_DETAIL]
        r = await client.post("/api/v1/configmaps/", headers=auth_headers, json={
            "name": "test-cm",
            "namespace": "pi-apps",
            "data": {"key": "value"},
        })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "test-cm"
    assert data["data"] == {"key": "value"}


@pytest.mark.asyncio
async def test_create_configmap_invalid_name_rejected(client, auth_headers):
    r = await client.post("/api/v1/configmaps/", headers=auth_headers, json={
        "name": "Bad Name!",
        "namespace": "pi-apps",
        "data": {},
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_configmap_duplicate_returns_409(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_configmap.return_value = MOCK_CM_DETAIL  # already exists
        r = await client.post("/api/v1/configmaps/", headers=auth_headers, json={
            "name": "existing-cm",
            "namespace": "pi-apps",
            "data": {},
        })
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_create_configmap_requires_admin(client):
    r = await client.post("/api/v1/configmaps/", json={
        "name": "new-cm",
        "namespace": "pi-apps",
        "data": {},
    })
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_configmap_viewer_forbidden(client, viewer_headers):
    r = await client.post("/api/v1/configmaps/", headers=viewer_headers, json={
        "name": "new-cm",
        "namespace": "pi-apps",
        "data": {},
    })
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_configmap_success(client, auth_headers):
    updated = dict(MOCK_CM_DETAIL, data={"key": "new-value"})
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_configmap.side_effect = [MOCK_CM_DETAIL, updated]
        MockK8s.return_value.update_configmap.return_value = None
        r = await client.put("/api/v1/configmaps/test-cm", headers=auth_headers,
                             json={"data": {"key": "new-value"}},
                             params={"namespace": "pi-apps"})
    assert r.status_code == 200
    assert r.json()["data"] == {"key": "new-value"}


@pytest.mark.asyncio
async def test_update_configmap_not_found_returns_404(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_configmap.return_value = None
        r = await client.put("/api/v1/configmaps/missing-cm", headers=auth_headers,
                             json={"data": {}},
                             params={"namespace": "pi-apps"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_configmap_requires_admin(client, viewer_headers):
    r = await client.put("/api/v1/configmaps/test-cm", headers=viewer_headers,
                         json={"data": {}})
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_configmap_success(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_configmap.return_value = MOCK_CM_DETAIL
        MockK8s.return_value.delete_configmap.return_value = None
        r = await client.delete("/api/v1/configmaps/test-cm", headers=auth_headers,
                                params={"namespace": "pi-apps"})
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_delete_configmap_not_found_returns_404(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_configmap.return_value = None
        r = await client.delete("/api/v1/configmaps/missing-cm", headers=auth_headers,
                                params={"namespace": "pi-apps"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_configmap_requires_admin(client):
    r = await client.delete("/api/v1/configmaps/test-cm")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_delete_configmap_viewer_forbidden(client, viewer_headers):
    r = await client.delete("/api/v1/configmaps/test-cm", headers=viewer_headers)
    assert r.status_code == 403
