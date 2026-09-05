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

    # Auto-login bridge for Wallabag's one shared account (docs/decisions.md)
    # - Wallabag has no reverse-proxy/OIDC pre-auth support of its own, so
    # this is the only way to skip its login screen. Never logged, never
    # returned to the frontend.
    wallabag_username: str = "wallabag"
    wallabag_password: str = "CHANGE_ME"

    # Vikunja's bridge (see docs/decisions.md) can't use one shared
    # credential like Wallabag's - it has two real distinct accounts, so
    # this maps pi-cluster username -> that same person's Vikunja password.
    # JSON object in .env, e.g. {"admin":"...","Yana":"..."}. A pi-cluster
    # user with no entry here just doesn't get the bridge - falls through
    # to Vikunja's own login, same as before any bridge existed.
    vikunja_bridge_credentials: dict[str, str] = {}

    # Brevo SMTP relay (docs/decisions.md) - shared with Vikunja's own
    # reminder mail (a separate credential set in its own K8s Secret, not
    # this one). Used for the "email" notification_channels type.
    brevo_smtp_host: str = "smtp-relay.brevo.com"
    brevo_smtp_port: int = 587
    brevo_smtp_username: str = ""
    brevo_smtp_password: str = ""
    brevo_alert_from_email: str = "alerts@cluster.download"

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
