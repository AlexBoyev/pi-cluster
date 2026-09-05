from datetime import datetime

from pydantic import BaseModel


class ChannelCreate(BaseModel):
    name: str
    channel_type: str = "webhook"  # "webhook" or "email"
    url: str | None = None
    email_address: str | None = None
    # "critical" default (not "warning" like the DB column) - a newly
    # created channel opts into the quieter behavior by default; loosen to
    # "warning" explicitly to receive every alert. Only applies to infra
    # alerts, never security events - see docs/decisions.md.
    min_severity: str = "critical"
    enabled: bool = True


class ChannelUpdate(BaseModel):
    name: str | None = None
    channel_type: str | None = None
    url: str | None = None
    email_address: str | None = None
    min_severity: str | None = None
    enabled: bool | None = None


class ChannelResponse(BaseModel):
    id: int
    name: str
    channel_type: str
    url: str | None
    email_address: str | None
    min_severity: str
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}
