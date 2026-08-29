from datetime import datetime

from pydantic import BaseModel


class ChannelCreate(BaseModel):
    name: str
    url: str
    enabled: bool = True


class ChannelUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    enabled: bool | None = None


class ChannelResponse(BaseModel):
    id: int
    name: str
    url: str
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}
