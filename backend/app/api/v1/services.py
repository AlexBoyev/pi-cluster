from fastapi import APIRouter, Depends, Query
from starlette.concurrency import run_in_threadpool

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.schemas.service import IngressInfo, ServiceInfo
from app.services.k8s_service import K8sService

router = APIRouter(tags=["services"])


@router.get("/services", response_model=list[ServiceInfo])
async def list_services(
    namespace: str | None = Query(None),
    _: User = Depends(get_current_user),
) -> list[ServiceInfo]:
    items = await run_in_threadpool(K8sService().list_services, namespace)
    return [ServiceInfo(**i) for i in items]


@router.get("/ingresses", response_model=list[IngressInfo])
async def list_ingresses(
    namespace: str | None = Query(None),
    _: User = Depends(get_current_user),
) -> list[IngressInfo]:
    items = await run_in_threadpool(K8sService().list_ingresses, namespace)
    return [IngressInfo(**i) for i in items]
