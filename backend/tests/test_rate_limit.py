"""Rate limiting on /auth/login. Disabled globally in conftest.py (session-
scoped client + many login-heavy tests would otherwise trip it) — this test
temporarily re-enables it in isolation to prove it actually works."""
import pytest

from app.rate_limit import limiter


@pytest.mark.asyncio
async def test_login_rate_limit_returns_429_after_10_per_minute(client):
    limiter.enabled = True
    limiter.reset()
    try:
        statuses = []
        for _ in range(12):
            r = await client.post(
                "/api/v1/auth/login",
                json={"username": "no-such-user", "password": "wrong"},
            )
            statuses.append(r.status_code)

        # First 10 are evaluated normally (401 — bad credentials); the rest
        # are rejected by the limiter itself before reaching the handler.
        assert statuses[:10] == [401] * 10
        assert 429 in statuses[10:]
    finally:
        limiter.enabled = False
        limiter.reset()
