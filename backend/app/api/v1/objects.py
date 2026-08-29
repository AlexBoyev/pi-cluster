from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.schemas.k8s_objects import DaemonSetInfo, StatefulSetInfo
from app.services.k8s_service import K8sService

router = APIRouter(prefix="/objects", tags=["objects"])


@router.get("/statefulsets", response_model=list[StatefulSetInfo])
async def list_statefulsets(namespace: str | None = None) -> list[StatefulSetInfo]:
    return await run_in_threadpool(K8sService().list_statefulsets, namespace)


@router.get("/daemonsets", response_model=list[DaemonSetInfo])
async def list_daemonsets(namespace: str | None = None) -> list[DaemonSetInfo]:
    return await run_in_threadpool(K8sService().list_daemonsets, namespace)
