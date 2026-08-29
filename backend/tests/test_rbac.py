import pytest
from unittest.mock import patch

MOCK_CLUSTER_ROLE = {
    "name": "cluster-admin",
    "rules_count": 1,
    "rules": [{"api_groups": ["*"], "resources": ["*"], "verbs": ["*"]}],
    "created_at": "2026-01-01T00:00:00Z",
}

MOCK_CLUSTER_ROLE_BINDING = {
    "name": "cluster-admin-binding",
    "role_kind": "ClusterRole",
    "role_name": "cluster-admin",
    "subjects": [{"kind": "User", "name": "admin", "namespace": None}],
    "created_at": "2026-01-01T00:00:00Z",
}

MOCK_SERVICE_ACCOUNT = {
    "name": "default",
    "namespace": "pi-apps",
    "secrets_count": 0,
    "created_at": "2026-01-01T00:00:00Z",
}

K8S_PATCH = "app.api.v1.rbac.K8sService"


@pytest.mark.asyncio
async def test_list_cluster_roles_empty(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_cluster_roles.return_value = []
        r = await client.get("/api/v1/rbac/clusterroles", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_cluster_roles_returns_data(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_cluster_roles.return_value = [MOCK_CLUSTER_ROLE]
        r = await client.get("/api/v1/rbac/clusterroles", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "cluster-admin"


@pytest.mark.asyncio
async def test_list_cluster_roles_hide_system_default(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_cluster_roles.return_value = []
        r = await client.get("/api/v1/rbac/clusterroles", headers=auth_headers)
    assert r.status_code == 200
    MockK8s.return_value.list_cluster_roles.assert_called_once_with(True)


@pytest.mark.asyncio
async def test_list_cluster_role_bindings_empty(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_cluster_role_bindings.return_value = []
        r = await client.get("/api/v1/rbac/clusterrolebindings", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_cluster_role_bindings_returns_data(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_cluster_role_bindings.return_value = [MOCK_CLUSTER_ROLE_BINDING]
        r = await client.get("/api/v1/rbac/clusterrolebindings", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()[0]["name"] == "cluster-admin-binding"


@pytest.mark.asyncio
async def test_list_service_accounts_empty(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_service_accounts.return_value = []
        r = await client.get("/api/v1/rbac/serviceaccounts", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_service_accounts_filter_namespace(client, auth_headers):
    with patch(K8S_PATCH) as MockK8s:
        MockK8s.return_value.list_service_accounts.return_value = [MOCK_SERVICE_ACCOUNT]
        r = await client.get("/api/v1/rbac/serviceaccounts?namespace=pi-apps", headers=auth_headers)
    assert r.status_code == 200
    MockK8s.return_value.list_service_accounts.assert_called_once_with("pi-apps")


@pytest.mark.asyncio
async def test_list_cluster_roles_no_auth(client):
    r = await client.get("/api/v1/rbac/clusterroles")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_cluster_role_bindings_no_auth(client):
    r = await client.get("/api/v1/rbac/clusterrolebindings")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_service_accounts_no_auth(client):
    r = await client.get("/api/v1/rbac/serviceaccounts")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_cluster_roles_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/rbac/clusterroles", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_list_cluster_role_bindings_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/rbac/clusterrolebindings", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_list_service_accounts_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/rbac/serviceaccounts", headers=viewer_headers)
    assert r.status_code == 403
