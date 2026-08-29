from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.schemas.quota import LimitRangeInfo, ResourceQuotaInfo
from app.services.k8s_service import K8sService

router = APIRouter(prefix="/quotas", tags=["quotas"])


@router.get("/resourcequotas", response_model=list[ResourceQuotaInfo])
async def list_resource_quotas(namespace: str | None = None) -> list[ResourceQuotaInfo]:
    items = await run_in_threadpool(K8sService().list_resource_quotas, namespace)
    return [ResourceQuotaInfo(**i) for i in items]


@router.get("/limitranges", response_model=list[LimitRangeInfo])
async def list_limit_ranges(namespace: str | None = None) -> list[LimitRangeInfo]:
    items = await run_in_threadpool(K8sService().list_limit_ranges, namespace)
    return [LimitRangeInfo(**i) for i in items]
