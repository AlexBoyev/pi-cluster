from pydantic import BaseModel


class HelmRelease(BaseModel):
    name: str
    namespace: str
    chart: str
    chart_version: str | None
    app_version: str | None
    status: str
    revision: int
    description: str | None
    first_deployed: str | None
    last_deployed: str | None
