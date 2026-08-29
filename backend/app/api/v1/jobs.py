from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.schemas.job import JobInfo
from app.services.k8s_service import K8sService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/", response_model=list[JobInfo])
async def list_jobs(namespace: str | None = None) -> list[JobInfo]:
    items = await run_in_threadpool(K8sService().list_jobs, namespace)
    return [JobInfo(**i) for i in items]
