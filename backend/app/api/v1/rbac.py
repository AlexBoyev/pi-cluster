from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.schemas.rbac import ClusterRoleBindingInfo, ClusterRoleInfo, ServiceAccountInfo
from app.services.k8s_service import K8sService

router = APIRouter(prefix="/rbac", tags=["rbac"])


@router.get("/clusterroles", response_model=list[ClusterRoleInfo])
async def list_cluster_roles(hide_system: bool = True) -> list[ClusterRoleInfo]:
    return await run_in_threadpool(K8sService().list_cluster_roles, hide_system)


@router.get("/clusterrolebindings", response_model=list[ClusterRoleBindingInfo])
async def list_cluster_role_bindings(
    hide_system: bool = True,
) -> list[ClusterRoleBindingInfo]:
    return await run_in_threadpool(
        K8sService().list_cluster_role_bindings, hide_system
    )


@router.get("/serviceaccounts", response_model=list[ServiceAccountInfo])
async def list_service_accounts(
    namespace: str | None = None,
) -> list[ServiceAccountInfo]:
    return await run_in_threadpool(K8sService().list_service_accounts, namespace)
