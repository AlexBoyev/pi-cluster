from datetime import datetime

from pydantic import BaseModel


class ChannelCreate(BaseModel):
    name: str
    channel_type: str = "webhook"  # "webhook" or "email"
    url: str | None = None
    email_address: str | None = None
    enabled: bool = True


class ChannelUpdate(BaseModel):
    name: str | None = None
    channel_type: str | None = None
    url: str | None = None
    email_address: str | None = None
    enabled: bool | None = None


class ChannelResponse(BaseModel):
    id: int
    name: str
    channel_type: str
    url: str | None
    email_address: str | None
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}
