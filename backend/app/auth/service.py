from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _make_token(data: dict, expires_delta: timedelta) -> str:
    payload = data | {"exp": datetime.now(timezone.utc) + expires_delta}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def create_access_token(username: str, role: str) -> str:
    return _make_token(
        {"sub": username, "role": role, "type": "access"},
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(username: str) -> str:
    return _make_token(
        {"sub": username, "type": "refresh"},
        timedelta(days=settings.jwt_refresh_token_expire_days),
    )


def create_sso_token(username: str) -> str:
    """Long-lived token for the cross-subdomain SSO cookie only - never
    returned to the SPA, never used for API auth."""
    return _make_token(
        {"sub": username, "type": "sso"},
        timedelta(days=settings.jwt_refresh_token_expire_days),
    )


def create_wallabag_bridge_token(session_id: str) -> str:
    """Carries a freshly-minted Wallabag PHPSESSID across the redirect to
    wallabag-sso-finish (see docs/decisions.md) - short-lived on purpose,
    it's a one-hop handoff, never stored anywhere. Signed so the raw session
    id never sits in plaintext in a URL or an access log."""
    return _make_token({"sid": session_id, "type": "wallabag_bridge"}, timedelta(seconds=30))


def create_vikunja_bridge_token(refresh_token: str, access_token: str) -> str:
    """Same one-hop handoff pattern as the Wallabag bridge token, carrying
    Vikunja's own refresh-token cookie value instead of a PHPSESSID. Also
    carries the access_token (JWT) from the login response body - Vikunja's
    frontend won't use the refresh cookie on its own on a fresh load, only
    localStorage['token'] (see vikunja_bridge_service.py)."""
    return _make_token(
        {"rt": refresh_token, "at": access_token, "type": "vikunja_bridge"},
        timedelta(seconds=30),
    )


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises JWTError on failure."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
