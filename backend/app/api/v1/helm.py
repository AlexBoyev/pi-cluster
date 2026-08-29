from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.schemas.helm import HelmRelease
from app.services.k8s_service import K8sService

router = APIRouter(prefix="/helm", tags=["helm"])


@router.get("/releases", response_model=list[HelmRelease])
async def list_helm_releases(namespace: str | None = None) -> list[HelmRelease]:
    return await run_in_threadpool(K8sService().list_helm_releases, namespace)
