import pytest


# ---------------------------------------------------------------------------
# Login success
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success(client):
    r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "adminpass123"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data


# ---------------------------------------------------------------------------
# Login validation failures
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_empty_username(client):
    r = await client.post("/api/v1/auth/login", json={"username": "", "password": "adminpass123"})
    # FastAPI will pass an empty string to the handler; the handler returns 401
    # because no user with username "" exists.
    assert r.status_code in (401, 422)


@pytest.mark.asyncio
async def test_login_empty_password(client):
    r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": ""})
    assert r.status_code in (401, 422)


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    r = await client.post("/api/v1/auth/login", json={"username": "nobody", "password": "anything"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_token_refresh(client):
    r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "adminpass123"})
    refresh = r.json()["refresh_token"]
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 200
    assert "access_token" in r2.json()


@pytest.mark.asyncio
async def test_token_refresh_with_invalid_token(client):
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-valid-token"})
    assert r.status_code in (401, 422)


@pytest.mark.asyncio
async def test_token_refresh_with_access_token_rejected(client):
    """An access token must not be accepted as a refresh token."""
    r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "adminpass123"})
    access = r.json()["access_token"]
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert r2.status_code == 401


# ---------------------------------------------------------------------------
# Protected routes require a valid token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_me_requires_auth(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_with_valid_token(client, auth_headers):
    r = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_protected_route_without_token_returns_403(client):
    """Users list is admin-only; no token should be rejected."""
    r = await client.get("/api/v1/users/")
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# User management (kept here for auth-related flows)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_users_admin(client, auth_headers):
    r = await client.get("/api/v1/users/", headers=auth_headers)
    assert r.status_code == 200
    users = r.json()
    assert any(u["username"] == "admin" for u in users)


@pytest.mark.asyncio
async def test_create_and_delete_user(client, auth_headers):
    r = await client.post("/api/v1/users/", headers=auth_headers, json={
        "username": "testuser_del",
        "password": "Testpass1!",
        "role": "viewer",
    })
    assert r.status_code in (200, 201)
    uid = r.json()["id"]
    r2 = await client.delete(f"/api/v1/users/{uid}", headers=auth_headers)
    assert r2.status_code in (200, 204)
