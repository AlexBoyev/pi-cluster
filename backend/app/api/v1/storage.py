from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from app.auth.dependencies import require_admin
from app.schemas.storage import PVCCreate, PVCInfo, PVInfo, StorageClassInfo
from app.services.k8s_service import K8sService

router = APIRouter(prefix="/storage", tags=["storage"])


@router.get("/classes", response_model=list[StorageClassInfo])
async def list_storage_classes() -> list[StorageClassInfo]:
    return await run_in_threadpool(K8sService().list_storage_classes)


@router.get("/pvcs", response_model=list[PVCInfo])
async def list_pvcs(namespace: str | None = None) -> list[PVCInfo]:
    return await run_in_threadpool(K8sService().list_pvcs, namespace)


@router.post("/pvcs", status_code=201)
async def create_pvc(body: PVCCreate, _=Depends(require_admin)) -> dict[str, str]:
    try:
        await run_in_threadpool(
            K8sService().create_pvc,
            body.name,
            body.namespace,
            body.storage_class,
            body.access_modes,
            body.size,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"name": body.name}


@router.delete("/pvcs/{namespace}/{name}", status_code=204)
async def delete_pvc(namespace: str, name: str, _=Depends(require_admin)) -> None:
    await run_in_threadpool(K8sService().delete_pvc, name, namespace)


@router.get("/pvs", response_model=list[PVInfo])
async def list_pvs() -> list[PVInfo]:
    return await run_in_threadpool(K8sService().list_pvs)
