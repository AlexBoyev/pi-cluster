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
        "jenkins": {
            "url": "https://jenkins.cluster.download",
            "username": "admin",
            "password": settings.jenkins_admin_password or "(not set — add JENKINS_ADMIN_PASSWORD to .env)",
        },
        "argocd": {
            "url": "https://argocd.cluster.download",
            "username": "admin",
            "password": settings.argocd_admin_password or "(not set — add ARGOCD_ADMIN_PASSWORD to .env)",
        },
        "paperless": {
            "url": "https://paperless.cluster.download",
            "username": settings.paperless_admin_user or "admin",
            "password": settings.paperless_admin_password or "(not set — add PAPERLESS_ADMIN_PASSWORD to .env)",
            "note": "SSO auto-logs in via Remote-User when already logged into pi-cluster — this is the Django superuser fallback, not needed day to day.",
        },
        "paperless_samba": {
            "note": "Consume-folder share, LAN-only — \\\\10.100.102.16\\inbox (Windows) or smb://10.100.102.16/inbox",
            "username": "paperless",
            "password": settings.paperless_samba_password or "(not set — add PAPERLESS_SAMBA_PASSWORD to .env)",
        },
        "prometheus": {
            "url": "https://prometheus.cluster.download",
            "note": "No authentication configured.",
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
