from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.auth.dependencies import get_current_user, require_admin
from app.models.user import User
from app.schemas.configmap import ConfigMapCreate, ConfigMapDetail, ConfigMapSummary, ConfigMapUpdate
from app.services.k8s_service import K8sService

router = APIRouter(prefix="/configmaps", tags=["configmaps"])


@router.get("/", response_model=list[ConfigMapSummary])
async def list_configmaps(
    namespace: str = "pi-apps",
    _: User = Depends(get_current_user),
) -> list[ConfigMapSummary]:
    k8s = K8sService()
    items = await run_in_threadpool(k8s.list_configmaps, namespace)
    return [ConfigMapSummary(**i) for i in items]


@router.get("/{name}", response_model=ConfigMapDetail)
async def get_configmap(
    name: str,
    namespace: str = "pi-apps",
    _: User = Depends(get_current_user),
) -> ConfigMapDetail:
    k8s = K8sService()
    result = await run_in_threadpool(k8s.get_configmap, name, namespace)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ConfigMap not found")
    return ConfigMapDetail(**result)


@router.post("/", response_model=ConfigMapDetail, status_code=201)
async def create_configmap(
    data: ConfigMapCreate,
    _: User = Depends(require_admin),
) -> ConfigMapDetail:
    k8s = K8sService()
    existing = await run_in_threadpool(k8s.get_configmap, data.name, data.namespace)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ConfigMap already exists")
    await run_in_threadpool(k8s.create_configmap, data.name, data.namespace, data.data)
    result = await run_in_threadpool(k8s.get_configmap, data.name, data.namespace)
    return ConfigMapDetail(**(result or {"name": data.name, "namespace": data.namespace, "data": data.data, "created_at": None}))


@router.put("/{name}", response_model=ConfigMapDetail)
async def update_configmap(
    name: str,
    body: ConfigMapUpdate,
    namespace: str = "pi-apps",
    _: User = Depends(require_admin),
) -> ConfigMapDetail:
    k8s = K8sService()
    if await run_in_threadpool(k8s.get_configmap, name, namespace) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ConfigMap not found")
    await run_in_threadpool(k8s.update_configmap, name, namespace, body.data)
    result = await run_in_threadpool(k8s.get_configmap, name, namespace)
    return ConfigMapDetail(**(result or {"name": name, "namespace": namespace, "data": body.data, "created_at": None}))


@router.delete("/{name}", status_code=204)
async def delete_configmap(
    name: str,
    namespace: str = "pi-apps",
    _: User = Depends(require_admin),
) -> None:
    k8s = K8sService()
    if await run_in_threadpool(k8s.get_configmap, name, namespace) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ConfigMap not found")
    await run_in_threadpool(k8s.delete_configmap, name, namespace)
