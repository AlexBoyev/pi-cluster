from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.auth.dependencies import get_current_user, require_admin
from app.models.user import User
from app.schemas.cronjob import CronJobCreate, CronJobInfo, JobRun
from app.services.k8s_service import K8sService

router = APIRouter(prefix="/cronjobs", tags=["cronjobs"])


@router.get("/", response_model=list[CronJobInfo])
async def list_cronjobs(
    namespace: str | None = None,
    _: User = Depends(get_current_user),
) -> list[CronJobInfo]:
    items = await run_in_threadpool(K8sService().list_cronjobs, namespace)
    return [CronJobInfo(**i) for i in items]


@router.post("/", response_model=CronJobInfo, status_code=201)
async def create_cronjob(
    data: CronJobCreate,
    _: User = Depends(require_admin),
) -> CronJobInfo:
    k8s = K8sService()
    await run_in_threadpool(
        k8s.create_cronjob,
        data.name, data.namespace, data.schedule,
        data.image, data.command, data.env_vars,
    )
    items = await run_in_threadpool(k8s.list_cronjobs, data.namespace)
    found = next((i for i in items if i["name"] == data.name), None)
    if not found:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="CronJob created but not found")
    return CronJobInfo(**found)


@router.patch("/{name}/suspend", response_model=CronJobInfo)
async def suspend_cronjob(
    name: str,
    namespace: str = "pi-apps",
    _: User = Depends(require_admin),
) -> CronJobInfo:
    k8s = K8sService()
    await run_in_threadpool(k8s.set_cronjob_suspend, name, namespace, True)
    items = await run_in_threadpool(k8s.list_cronjobs, namespace)
    found = next((i for i in items if i["name"] == name), None)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CronJob not found")
    return CronJobInfo(**found)


@router.patch("/{name}/resume", response_model=CronJobInfo)
async def resume_cronjob(
    name: str,
    namespace: str = "pi-apps",
    _: User = Depends(require_admin),
) -> CronJobInfo:
    k8s = K8sService()
    await run_in_threadpool(k8s.set_cronjob_suspend, name, namespace, False)
    items = await run_in_threadpool(k8s.list_cronjobs, namespace)
    found = next((i for i in items if i["name"] == name), None)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CronJob not found")
    return CronJobInfo(**found)


@router.get("/{name}/jobs", response_model=list[JobRun])
async def list_cronjob_jobs(
    name: str,
    namespace: str = "pi-apps",
    _: User = Depends(get_current_user),
) -> list[JobRun]:
    items = await run_in_threadpool(K8sService().list_cronjob_jobs, name, namespace)
    return [JobRun(**i) for i in items]


@router.delete("/{name}", status_code=204)
async def delete_cronjob(
    name: str,
    namespace: str = "pi-apps",
    _: User = Depends(require_admin),
) -> None:
    await run_in_threadpool(K8sService().delete_cronjob, name, namespace)
