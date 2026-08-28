import logging

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from kubernetes.client.exceptions import ApiException

from app.models.workload import WorkloadStatus
from app.repositories.workload_repository import WorkloadRepository
from app.schemas.workload import NodeCapacity, WorkloadCreate, WorkloadResponse
from app.services.k8s_service import K8sService

logger = logging.getLogger(__name__)


class WorkloadService:
    def __init__(self, repo: WorkloadRepository, k8s: K8sService) -> None:
        self._repo = repo
        self._k8s = k8s

    async def list_workloads(self) -> list[WorkloadResponse]:
        workloads = await self._repo.get_all()
        result = []
        for w in workloads:
            if w.status == WorkloadStatus.DELETED:
                continue
            try:
                ready = await run_in_threadpool(self._k8s.get_ready_replicas, w.name, w.namespace)
            except Exception:
                ready = 0
            result.append(WorkloadResponse(
                id=w.id,
                name=w.name,
                namespace=w.namespace,
                image=w.image,
                replicas=w.replicas,
                ready_replicas=ready,
                target_node=w.target_node,
                status=w.status,
                created_at=w.created_at,
            ))
        return result

    async def create_workload(self, data: WorkloadCreate) -> WorkloadResponse:
        existing = await self._repo.get_by_name(data.name)
        if existing and existing.status != WorkloadStatus.DELETED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workload already exists")

        target_node = data.target_node
        if target_node is None:
            try:
                target_node = await run_in_threadpool(self._k8s.pick_best_node)
            except Exception as e:
                logger.warning("Capacity-aware placement failed: %s — deploying without node selector", e)

        try:
            await run_in_threadpool(
                self._k8s.create_deployment,
                data.name, data.namespace, data.image, data.replicas,
                target_node, data.cpu_request, data.memory_request,
            )
        except ApiException as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")

        resolved = data.model_copy(update={"target_node": target_node})
        workload = await self._repo.create(resolved)
        await self._repo.update_status(workload.name, WorkloadStatus.RUNNING)

        return WorkloadResponse(
            id=workload.id,
            name=workload.name,
            namespace=workload.namespace,
            image=workload.image,
            replicas=workload.replicas,
            ready_replicas=0,
            target_node=workload.target_node,
            status=WorkloadStatus.RUNNING,
            created_at=workload.created_at,
        )

    async def delete_workload(self, name: str) -> None:
        workload = await self._repo.get_by_name(name)
        if workload is None or workload.status == WorkloadStatus.DELETED:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workload not found")
        try:
            await run_in_threadpool(self._k8s.delete_deployment, name, workload.namespace)
        except ApiException as e:
            if e.status != 404:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")
        await self._repo.update_status(name, WorkloadStatus.DELETED)

    async def get_node_capacities(self) -> list[NodeCapacity]:
        try:
            return await run_in_threadpool(self._k8s.get_node_capacities)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e}")

    async def cordon_node(self, node_name: str) -> None:
        try:
            await run_in_threadpool(self._k8s.cordon_node, node_name)
        except ApiException as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")

    async def uncordon_node(self, node_name: str) -> None:
        try:
            await run_in_threadpool(self._k8s.uncordon_node, node_name)
        except ApiException as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")
