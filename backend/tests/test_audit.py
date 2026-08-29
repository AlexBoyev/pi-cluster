import pytest


@pytest.mark.asyncio
async def test_list_audit_log(client, auth_headers):
    r = await client.get("/api/v1/audit/", headers=auth_headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_audit_requires_auth(client):
    r = await client.get("/api/v1/audit/")
    assert r.status_code in (401, 403)
