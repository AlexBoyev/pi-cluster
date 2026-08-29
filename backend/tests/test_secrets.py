"""Secret CRUD lifecycle, validation, and admin-only permission tests."""
import pytest
from unittest.mock import patch, MagicMock

K8S_PATCH = "app.api.v1.secrets.K8sService"

MOCK_SECRET_SUMMARY = {
    "name": "test-secret",
    "namespace": "pi-apps",
    "type": "Opaque",
    "data_keys": ["password"],
    "created_at": None,
}

MOCK_SECRET_DETAIL = {
    "name": "test-secret",
    "namespace": "pi-apps",
    "type": "Opaque",
    "data": {"password": "s3cr3t"},
    "created_at": None,
}

VALID_CREATE_BODY = {
    "name": "test-secret",
    "namespace": "pi-apps",
    "type": "Opaque",
    "data": {"password": "s3cr3t"},
}


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_secrets_admin(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_secrets.return_value = []
        r = await client.get("/api/v1/secrets/", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_list_secrets_with_data(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_secrets.return_value = [MOCK_SECRET_SUMMARY]
        r = await client.get("/api/v1/secrets/", headers=auth_headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["name"] == "test-secret"


@pytest.mark.asyncio
async def test_list_secrets_requires_admin(client):
    r = await client.get("/api/v1/secrets/")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_secrets_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/secrets/", headers=viewer_headers)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# GET by name
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_secret_success(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_secret.return_value = MOCK_SECRET_DETAIL
        r = await client.get("/api/v1/secrets/test-secret", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "test-secret"
    assert "data" in data


@pytest.mark.asyncio
async def test_get_secret_not_found(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_secret.return_value = None
        r = await client.get("/api/v1/secrets/no-such-secret", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_secret_requires_admin(client, viewer_headers):
    r = await client.get("/api/v1/secrets/test-secret", headers=viewer_headers)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_secret_success(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_secret.return_value = None  # does not exist
        MockK8s.return_value.create_secret.return_value = None
        MockK8s.return_value.list_secrets.return_value = [MOCK_SECRET_SUMMARY]
        r = await client.post("/api/v1/secrets/", headers=auth_headers, json=VALID_CREATE_BODY)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "test-secret"
    assert "data_keys" in data


@pytest.mark.asyncio
async def test_create_secret_invalid_name_returns_422(client, auth_headers):
    r = await client.post("/api/v1/secrets/", headers=auth_headers, json={
        "name": "Bad_Name!",
        "namespace": "pi-apps",
        "data": {},
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_secret_uppercase_name_returns_422(client, auth_headers):
    r = await client.post("/api/v1/secrets/", headers=auth_headers, json={
        "name": "MySecret",
        "namespace": "pi-apps",
        "data": {},
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_secret_duplicate_returns_409(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_secret.return_value = MOCK_SECRET_DETAIL  # already exists
        r = await client.post("/api/v1/secrets/", headers=auth_headers, json=VALID_CREATE_BODY)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_create_secret_requires_admin(client):
    r = await client.post("/api/v1/secrets/", json=VALID_CREATE_BODY)
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_secret_viewer_forbidden(client, viewer_headers):
    r = await client.post("/api/v1/secrets/", headers=viewer_headers, json=VALID_CREATE_BODY)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_secret_success(client, auth_headers):
    updated_summary = dict(MOCK_SECRET_SUMMARY, data_keys=["new-key"])
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_secret.return_value = MOCK_SECRET_DETAIL
        MockK8s.return_value.update_secret.return_value = None
        MockK8s.return_value.list_secrets.return_value = [updated_summary]
        r = await client.put("/api/v1/secrets/test-secret", headers=auth_headers,
                             json={"data": {"new-key": "new-value"}},
                             params={"namespace": "pi-apps"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_update_secret_not_found_returns_404(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_secret.return_value = None
        r = await client.put("/api/v1/secrets/missing-secret", headers=auth_headers,
                             json={"data": {}},
                             params={"namespace": "pi-apps"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_secret_viewer_forbidden(client, viewer_headers):
    r = await client.put("/api/v1/secrets/test-secret", headers=viewer_headers,
                         json={"data": {}})
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_secret_success(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_secret.return_value = MOCK_SECRET_DETAIL
        MockK8s.return_value.delete_secret.return_value = None
        r = await client.delete("/api/v1/secrets/test-secret", headers=auth_headers,
                                params={"namespace": "pi-apps"})
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_delete_secret_not_found_returns_404(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.get_secret.return_value = None
        r = await client.delete("/api/v1/secrets/missing-secret", headers=auth_headers,
                                params={"namespace": "pi-apps"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_secret_requires_admin(client):
    r = await client.delete("/api/v1/secrets/test-secret")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_delete_secret_viewer_forbidden(client, viewer_headers):
    r = await client.delete("/api/v1/secrets/test-secret", headers=viewer_headers)
    assert r.status_code == 403
