import base64

from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/vault", tags=["vault"])


def _argocd_password() -> str:
    try:
        from kubernetes import client as k8s_client, config as k8s_config
        k8s_config.load_kube_config(config_file=settings.k8s_kubeconfig_path)
        secret = k8s_client.CoreV1Api().read_namespaced_secret(
            "argocd-initial-admin-secret", "argocd"
        )
        return base64.b64decode(secret.data["password"]).decode().strip()
    except Exception:
        return "(unavailable — secret not found in argocd namespace)"


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
            "password": _argocd_password(),
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
