import pytest


@pytest.mark.asyncio
async def test_login_success(client):
    r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "adminpass123"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    r = await client.post("/api/v1/auth/login", json={"username": "nobody", "password": "x"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_list_users_requires_auth(client):
    r = await client.get("/api/v1/users/")
    assert r.status_code == 403  # or 401


@pytest.mark.asyncio
async def test_list_users_admin(client, auth_headers):
    r = await client.get("/api/v1/users/", headers=auth_headers)
    assert r.status_code == 200
    users = r.json()
    assert any(u["username"] == "admin" for u in users)


@pytest.mark.asyncio
async def test_create_and_delete_user(client, auth_headers):
    # Create
    r = await client.post("/api/v1/users/", headers=auth_headers, json={
        "username": "testuser_del",
        "password": "Testpass1!",
        "role": "viewer",
    })
    assert r.status_code in (200, 201)
    uid = r.json()["id"]
    # Delete
    r2 = await client.delete(f"/api/v1/users/{uid}", headers=auth_headers)
    assert r2.status_code in (200, 204)


@pytest.mark.asyncio
async def test_token_refresh(client):
    r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "adminpass123"})
    refresh = r.json()["refresh_token"]
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 200
    assert "access_token" in r2.json()
