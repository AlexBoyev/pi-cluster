from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from app.services.k8s_service import K8sService

router = APIRouter(prefix="/pods", tags=["pods"])


@router.get("/")
async def list_pods(namespace: str = Query("default")) -> list[dict]:
    return await run_in_threadpool(K8sService().list_pods_in_namespace, namespace)


@router.get("/{namespace}/{name}")
async def get_pod_detail(namespace: str, name: str) -> dict:
    return await run_in_threadpool(K8sService().get_pod_detail, name, namespace)
