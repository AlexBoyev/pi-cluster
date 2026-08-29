from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.auth.dependencies import require_admin
from app.schemas.namespace import NamespaceCreate, NamespaceInfo
from app.services.k8s_service import K8sService

router = APIRouter(prefix="/namespaces", tags=["namespaces"])

_PROTECTED = frozenset({
    "default", "kube-system", "kube-public", "kube-node-lease",
    "monitoring", "argocd",
})


@router.get("/", response_model=list[NamespaceInfo])
async def list_namespaces() -> list[NamespaceInfo]:
    k8s = K8sService()
    return [NamespaceInfo(**n) for n in await run_in_threadpool(k8s.list_namespaces)]


@router.post("/", response_model=NamespaceInfo, status_code=status.HTTP_201_CREATED)
async def create_namespace(data: NamespaceCreate, _=Depends(require_admin)) -> NamespaceInfo:
    if data.name in _PROTECTED:
        raise HTTPException(status_code=400, detail=f"'{data.name}' is a protected namespace")
    k8s = K8sService()
    await run_in_threadpool(k8s.create_namespace, data.name)
    raw = await run_in_threadpool(k8s.list_namespaces)
    ns = next((n for n in raw if n["name"] == data.name), None)
    if not ns:
        raise HTTPException(status_code=404, detail="Namespace not found after creation")
    return NamespaceInfo(**ns)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_namespace(name: str, _=Depends(require_admin)) -> None:
    if name in _PROTECTED:
        raise HTTPException(status_code=400, detail=f"'{name}' is a protected namespace")
    k8s = K8sService()
    await run_in_threadpool(k8s.delete_namespace, name)
