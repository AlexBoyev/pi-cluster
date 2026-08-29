from datetime import datetime

from pydantic import BaseModel, Field


class CronJobInfo(BaseModel):
    name: str
    namespace: str
    schedule: str
    suspended: bool
    active_jobs: int
    last_schedule_time: datetime | None
    image: str
    created_at: datetime | None


class CronJobCreate(BaseModel):
    name: str = Field(..., pattern=r"^[a-z][a-z0-9-]{0,62}$")
    namespace: str = "pi-apps"
    schedule: str = Field(..., min_length=1)
    image: str = Field(..., min_length=1)
    command: list[str] = Field(default_factory=list)
    env_vars: dict[str, str] = Field(default_factory=dict)


class JobRun(BaseModel):
    name: str
    succeeded: int
    failed: int
    active: int
    start_time: datetime | None
    completion_time: datetime | None
