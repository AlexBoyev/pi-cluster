from datetime import datetime

from pydantic import BaseModel


class PolicyRule(BaseModel):
    api_groups: list[str]
    resources: list[str]
    verbs: list[str]


class ClusterRoleInfo(BaseModel):
    name: str
    rules_count: int
    rules: list[PolicyRule]
    created_at: datetime | None


class RoleSubject(BaseModel):
    kind: str
    name: str
    namespace: str | None


class ClusterRoleBindingInfo(BaseModel):
    name: str
    role_kind: str | None
    role_name: str | None
    subjects: list[RoleSubject]
    created_at: datetime | None


class ServiceAccountInfo(BaseModel):
    name: str
    namespace: str | None
    secrets_count: int
    created_at: datetime | None
