from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    app_name: str = "pi-cluster"
    environment: str = "development"
    log_level: str = "INFO"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    database_url: str
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "pi_cluster"
    postgres_user: str = "pi_cluster"
    postgres_password: str = "CHANGE_ME"

    redis_url: str = "redis://redis:6379/0"

    ssh_username: str = "admin"
    ssh_password: str = "CHANGE_ME"
    ssh_connect_timeout: int = 10
    ssh_command_timeout: int = 15

    jwt_secret_key: str = "CHANGE_ME"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    admin_default_password: str = "admin123"

    # Cross-subdomain SSO cookie so household services (Wallabag, etc.) behind
    # nginx's wildcard fallback can gate on "already logged into pi-cluster"
    # without sharing credentials with those apps' own user systems. Set on
    # both domains on every login - a cookie's Domain attribute must match
    # the host that issued it, and the platform is reachable on either
    # pi-cluster.lan (LAN) or pi.cluster.download (LAN split-horizon today,
    # public later), so only one of the two actually sticks per login,
    # whichever matches the host the browser is actually on.
    sso_cookie_name: str = "pi_sso"
    sso_cookie_domains: list[str] = [".pi-cluster.lan", ".cluster.download"]

    prometheus_url: str = "http://prometheus:9090"
    alertmanager_url: str = "http://alertmanager:9093"
    grafana_url: str = "http://grafana:3000"
    grafana_admin_user: str = "admin"
    grafana_admin_password: str = "CHANGE_ME"

    jenkins_admin_password: str = ""

    log_retention_days: int = 90

    k8s_kubeconfig_path: str = "/app/kubeconfig"
    k8s_api_host: str = "10.100.102.10"
    k8s_namespace: str = "pi-apps"


settings = Settings()
