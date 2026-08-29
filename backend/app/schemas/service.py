from datetime import datetime

from pydantic import BaseModel


class ServicePort(BaseModel):
    port: int
    target_port: str | None
    node_port: int | None
    protocol: str


class ServiceInfo(BaseModel):
    name: str
    namespace: str
    type: str
    cluster_ip: str | None
    external_ip: str | None
    ports: list[ServicePort]
    selector: dict[str, str]
    created_at: datetime | None


class IngressPath(BaseModel):
    path: str
    backend_service: str | None
    backend_port: int | None


class IngressRule(BaseModel):
    host: str | None
    paths: list[IngressPath]


class IngressInfo(BaseModel):
    name: str
    namespace: str
    rules: list[IngressRule]
    tls_hosts: list[str]
    ingress_class: str | None
    created_at: datetime | None
