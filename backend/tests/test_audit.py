"""Audit log tests: listing, authentication, filtering, and pagination."""
import pytest
from unittest.mock import patch

K8S_SERVICE_PATCH = "app.api.v1.workloads.K8sService"


# ---------------------------------------------------------------------------
# Basic listing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_audit_log_returns_list(client, auth_headers):
    r = await client.get("/api/v1/audit/", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_list_audit_log_requires_auth(client):
    """The audit router is protected by get_current_user at the router level."""
    r = await client.get("/api/v1/audit/")
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Entries are created by workload operations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_entries_created_after_workload_create(client, auth_headers):
    """Creating a workload should produce an audit log entry."""
    with patch(K8S_SERVICE_PATCH) as MockK8s:
        MockK8s.return_value.create_deployment.return_value = None
        MockK8s.return_value.pick_best_node.return_value = None
        MockK8s.return_value.get_ready_replicas.return_value = 0
        r = await client.post("/api/v1/workloads/", headers=auth_headers, json={
            "name": "audit-test-wl",
            "image": "nginx:alpine",
            "replicas": 1,
        })
    assert r.status_code == 201

    # Audit log should now contain an entry for this workload
    r2 = await client.get("/api/v1/audit/", headers=auth_headers)
    assert r2.status_code == 200
    entries = r2.json()
    assert any(e["resource_name"] == "audit-test-wl" for e in entries)

    # Cleanup
    with patch(K8S_SERVICE_PATCH) as MockK8s:
        MockK8s.return_value.delete_deployment.return_value = None
        await client.delete("/api/v1/workloads/audit-test-wl", headers=auth_headers)


# ---------------------------------------------------------------------------
# Filter by status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_filter_by_status_success(client, auth_headers):
    r = await client.get("/api/v1/audit/?status=success", headers=auth_headers)
    assert r.status_code == 200
    entries = r.json()
    # All returned entries must have status=success
    for e in entries:
        assert e["status"] == "success"


@pytest.mark.asyncio
async def test_audit_filter_by_status_failure(client, auth_headers):
    r = await client.get("/api/v1/audit/?status=failure", headers=auth_headers)
    assert r.status_code == 200
    entries = r.json()
    for e in entries:
        assert e["status"] == "failure"


# ---------------------------------------------------------------------------
# Filter by resource type
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_filter_by_resource_type(client, auth_headers):
    r = await client.get("/api/v1/audit/?resource_type=workload", headers=auth_headers)
    assert r.status_code == 200
    entries = r.json()
    for e in entries:
        assert e["resource_type"] == "workload"


# ---------------------------------------------------------------------------
# Pagination: limit and offset
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_pagination_limit(client, auth_headers):
    r = await client.get("/api/v1/audit/?limit=2", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) <= 2


@pytest.mark.asyncio
async def test_audit_pagination_limit_1(client, auth_headers):
    r = await client.get("/api/v1/audit/?limit=1", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) <= 1


@pytest.mark.asyncio
async def test_audit_pagination_offset(client, auth_headers):
    r_all = await client.get("/api/v1/audit/?limit=100", headers=auth_headers)
    r_offset = await client.get("/api/v1/audit/?limit=100&offset=1", headers=auth_headers)
    assert r_all.status_code == 200
    assert r_offset.status_code == 200
    all_entries = r_all.json()
    offset_entries = r_offset.json()
    if len(all_entries) > 1:
        # The first item in offset result should be the second item in full result
        assert offset_entries[0]["id"] == all_entries[1]["id"]


@pytest.mark.asyncio
async def test_audit_limit_too_low_rejected(client, auth_headers):
    r = await client.get("/api/v1/audit/?limit=0", headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_audit_limit_too_high_rejected(client, auth_headers):
    r = await client.get("/api/v1/audit/?limit=501", headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_audit_negative_offset_rejected(client, auth_headers):
    r = await client.get("/api/v1/audit/?offset=-1", headers=auth_headers)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_entry_has_expected_fields(client, auth_headers):
    """Verify that a non-empty audit log contains properly shaped entries."""
    r = await client.get("/api/v1/audit/?limit=1", headers=auth_headers)
    assert r.status_code == 200
    entries = r.json()
    if entries:
        entry = entries[0]
        for field in ("id", "action", "resource_type", "resource_name", "actor", "status", "created_at"):
            assert field in entry, f"Missing field: {field}"
