"""User management CRUD, validation, and role-based access control tests."""
import pytest


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_users_admin(client, auth_headers):
    r = await client.get("/api/v1/users/", headers=auth_headers)
    assert r.status_code == 200
    users = r.json()
    assert isinstance(users, list)
    assert any(u["username"] == "admin" for u in users)


@pytest.mark.asyncio
async def test_list_users_without_auth(client):
    r = await client.get("/api/v1/users/")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_users_viewer_forbidden(client, viewer_headers):
    r = await client.get("/api/v1/users/", headers=viewer_headers)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_user_admin_success(client, auth_headers):
    r = await client.post("/api/v1/users/", headers=auth_headers, json={
        "username": "newviewer",
        "password": "Passw0rd!",
        "role": "viewer",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["username"] == "newviewer"
    assert data["role"] == "viewer"
    assert "id" in data
    assert "is_active" in data

    # Cleanup
    await client.delete(f"/api/v1/users/{data['id']}", headers=auth_headers)


@pytest.mark.asyncio
async def test_create_admin_user(client, auth_headers):
    r = await client.post("/api/v1/users/", headers=auth_headers, json={
        "username": "newadmin",
        "password": "Adminpass1!",
        "role": "admin",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["role"] == "admin"

    # Cleanup
    await client.delete(f"/api/v1/users/{data['id']}", headers=auth_headers)


@pytest.mark.asyncio
async def test_create_user_duplicate_username_returns_409(client, auth_headers):
    # First create
    r = await client.post("/api/v1/users/", headers=auth_headers, json={
        "username": "dupuser",
        "password": "Password1!",
        "role": "viewer",
    })
    assert r.status_code == 201
    uid = r.json()["id"]

    # Duplicate
    r2 = await client.post("/api/v1/users/", headers=auth_headers, json={
        "username": "dupuser",
        "password": "Password1!",
        "role": "viewer",
    })
    assert r2.status_code == 409

    # Cleanup
    await client.delete(f"/api/v1/users/{uid}", headers=auth_headers)


@pytest.mark.asyncio
async def test_create_user_username_too_short_returns_422(client, auth_headers):
    r = await client.post("/api/v1/users/", headers=auth_headers, json={
        "username": "ab",  # min_length=3
        "password": "Password1!",
        "role": "viewer",
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_user_weak_password_returns_422(client, auth_headers):
    r = await client.post("/api/v1/users/", headers=auth_headers, json={
        "username": "weakpwuser",
        "password": "short",  # min_length=8
        "role": "viewer",
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_user_invalid_role_returns_422(client, auth_headers):
    r = await client.post("/api/v1/users/", headers=auth_headers, json={
        "username": "badroleuser",
        "password": "Password1!",
        "role": "superuser",  # only admin|viewer allowed
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_user_requires_admin(client):
    r = await client.post("/api/v1/users/", json={
        "username": "anotheruser",
        "password": "Password1!",
        "role": "viewer",
    })
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_user_viewer_forbidden(client, viewer_headers):
    r = await client.post("/api/v1/users/", headers=viewer_headers, json={
        "username": "yetanotheruser",
        "password": "Password1!",
        "role": "viewer",
    })
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_user_admin_success(client, auth_headers):
    r = await client.post("/api/v1/users/", headers=auth_headers, json={
        "username": "todelete",
        "password": "Password1!",
        "role": "viewer",
    })
    assert r.status_code == 201
    uid = r.json()["id"]

    r2 = await client.delete(f"/api/v1/users/{uid}", headers=auth_headers)
    assert r2.status_code == 204


@pytest.mark.asyncio
async def test_delete_nonexistent_user_returns_404(client, auth_headers):
    r = await client.delete("/api/v1/users/999999", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_requires_admin(client):
    r = await client.delete("/api/v1/users/1")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_delete_user_viewer_forbidden(client, viewer_headers):
    r = await client.delete("/api/v1/users/1", headers=viewer_headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_cannot_delete_themselves(client, auth_headers, admin_token):
    """Look up the admin user id and attempt self-deletion."""
    r = await client.get("/api/v1/users/", headers=auth_headers)
    users = r.json()
    admin_user = next(u for u in users if u["username"] == "admin")
    r2 = await client.delete(f"/api/v1/users/{admin_user['id']}", headers=auth_headers)
    assert r2.status_code == 400


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_user_response_has_expected_fields(client, auth_headers):
    r = await client.post("/api/v1/users/", headers=auth_headers, json={
        "username": "fieldcheck",
        "password": "Password1!",
        "role": "viewer",
    })
    assert r.status_code == 201
    data = r.json()
    for field in ("id", "username", "role", "is_active", "created_at"):
        assert field in data, f"Missing field: {field}"

    await client.delete(f"/api/v1/users/{data['id']}", headers=auth_headers)
