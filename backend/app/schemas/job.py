from pydantic import BaseModel


class JobInfo(BaseModel):
    name: str
    namespace: str
    state: str
    active: int
    succeeded: int
    failed: int
    cron_job: str | None
    start_time: str | None
    completion_time: str | None
    created_at: str | None
