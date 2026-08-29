from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.auth.dependencies import require_admin
from app.schemas.storage import PVCInfo, PVInfo
from app.services.k8s_service import K8sService

router = APIRouter(prefix="/storage", tags=["storage"])


@router.get("/pvcs", response_model=list[PVCInfo])
async def list_pvcs(namespace: str | None = None) -> list[PVCInfo]:
    return await run_in_threadpool(K8sService().list_pvcs, namespace)


@router.delete("/pvcs/{namespace}/{name}", status_code=204)
async def delete_pvc(namespace: str, name: str, _=Depends(require_admin)) -> None:
    await run_in_threadpool(K8sService().delete_pvc, name, namespace)


@router.get("/pvs", response_model=list[PVInfo])
async def list_pvs() -> list[PVInfo]:
    return await run_in_threadpool(K8sService().list_pvs)
