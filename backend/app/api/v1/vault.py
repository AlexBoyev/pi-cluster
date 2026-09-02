from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/vault", tags=["vault"])


@router.get("")
async def get_vault() -> dict:
    return {
        "postgresql": {
            "host": settings.postgres_host,
            "port": settings.postgres_port,
            "database": settings.postgres_db,
            "username": settings.postgres_user,
            "password": settings.postgres_password,
        },
        "redis": {
            "url": settings.redis_url,
        },
        "ssh": {
            "username": settings.ssh_username,
            "password": settings.ssh_password,
        },
        "grafana": {
            "url": settings.grafana_url,
            "username": settings.grafana_admin_user,
            "password": settings.grafana_admin_password,
        },
        "app_admin": {
            "username": "admin",
            "password": settings.admin_default_password,
            "note": "Initial seed password — change via Users page after first login.",
        },
        "jwt": {
            "secret_key": settings.jwt_secret_key,
        },
    }
