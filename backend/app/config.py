from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    app_name: str = "pi-cluster"
    environment: str = "development"
    log_level: str = "INFO"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    database_url: str

    redis_url: str = "redis://redis:6379/0"

    ssh_username: str = "admin"
    ssh_password: str = "CHANGE_ME"
    ssh_connect_timeout: int = 10
    ssh_command_timeout: int = 15

    jwt_secret_key: str = "CHANGE_ME"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    admin_default_password: str = "admin123"

    prometheus_url: str = "http://prometheus:9090"
    alertmanager_url: str = "http://alertmanager:9093"
    grafana_url: str = "http://grafana:3000"
    grafana_admin_user: str = "admin"
    grafana_admin_password: str = "CHANGE_ME"

    k8s_kubeconfig_path: str = "/app/kubeconfig"
    k8s_api_host: str = "10.100.102.10"
    k8s_namespace: str = "pi-apps"


settings = Settings()
