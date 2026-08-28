from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


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


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises JWTError on failure."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
