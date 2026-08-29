from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.auth.dependencies import get_current_user, require_admin
from app.models.user import User
from app.schemas.secret import SecretCreate, SecretDetail, SecretSummary, SecretUpdate
from app.services.k8s_service import K8sService

router = APIRouter(prefix="/secrets", tags=["secrets"])


@router.get("/", response_model=list[SecretSummary])
async def list_secrets(
    namespace: str = "pi-apps",
    _: User = Depends(require_admin),
) -> list[SecretSummary]:
    items = await run_in_threadpool(K8sService().list_secrets, namespace)
    return [SecretSummary(**i) for i in items]


@router.get("/{name}", response_model=SecretDetail)
async def get_secret(
    name: str,
    namespace: str = "pi-apps",
    _: User = Depends(require_admin),
) -> SecretDetail:
    result = await run_in_threadpool(K8sService().get_secret, name, namespace)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    return SecretDetail(**result)


@router.post("/", response_model=SecretSummary, status_code=201)
async def create_secret(
    data: SecretCreate,
    _: User = Depends(require_admin),
) -> SecretSummary:
    k8s = K8sService()
    existing = await run_in_threadpool(k8s.get_secret, data.name, data.namespace)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Secret already exists")
    await run_in_threadpool(k8s.create_secret, data.name, data.namespace, data.data, data.type)
    items = await run_in_threadpool(k8s.list_secrets, data.namespace)
    found = next((i for i in items if i["name"] == data.name), None)
    return SecretSummary(**(found or {"name": data.name, "namespace": data.namespace, "type": data.type, "data_keys": list(data.data.keys()), "created_at": None}))


@router.put("/{name}", response_model=SecretSummary)
async def update_secret(
    name: str,
    body: SecretUpdate,
    namespace: str = "pi-apps",
    _: User = Depends(require_admin),
) -> SecretSummary:
    k8s = K8sService()
    existing = await run_in_threadpool(k8s.get_secret, name, namespace)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    await run_in_threadpool(k8s.update_secret, name, namespace, body.data)
    items = await run_in_threadpool(k8s.list_secrets, namespace)
    found = next((i for i in items if i["name"] == name), None)
    return SecretSummary(**(found or {"name": name, "namespace": namespace, "type": existing["type"], "data_keys": list(body.data.keys()), "created_at": None}))


@router.delete("/{name}", status_code=204)
async def delete_secret(
    name: str,
    namespace: str = "pi-apps",
    _: User = Depends(require_admin),
) -> None:
    k8s = K8sService()
    if await run_in_threadpool(k8s.get_secret, name, namespace) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    await run_in_threadpool(k8s.delete_secret, name, namespace)
