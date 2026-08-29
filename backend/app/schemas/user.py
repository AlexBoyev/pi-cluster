from datetime import datetime

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8)
    role: str = Field("viewer", pattern=r"^(admin|viewer)$")


class PasswordChange(BaseModel):
    new_password: str = Field(..., min_length=8)


class RoleUpdate(BaseModel):
    role: str = Field(..., pattern=r"^(admin|viewer)$")
