from pydantic import BaseModel


class QuotaResource(BaseModel):
    resource: str
    hard: str
    used: str


class ResourceQuotaInfo(BaseModel):
    name: str
    namespace: str
    resources: list[QuotaResource]
    created_at: str | None


class LimitRangeItem(BaseModel):
    type: str
    resource: str
    max: str | None
    min: str | None
    default: str | None
    default_request: str | None


class LimitRangeInfo(BaseModel):
    name: str
    namespace: str
    limits: list[LimitRangeItem]
    created_at: str | None
