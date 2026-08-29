import logging
from asyncio import gather as asyncio_gather

import httpx
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from kubernetes.client.exceptions import ApiException

from app.config import settings
from app.models.workload import WorkloadStatus
from app.repositories.workload_repository import WorkloadRepository
from app.schemas.workload import DeploymentRevision, NodeCapacity, PodInfo, WorkloadCreate, WorkloadEnvUpdate, WorkloadEvent, WorkloadHistory, WorkloadImageUpdate, WorkloadLogs, WorkloadMetrics, WorkloadProbeUpdate, WorkloadResourceUpdate, WorkloadResponse
from app.services.audit_service import AuditService
from app.services.k8s_service import K8sService


def _parse_cpu(s: str) -> float:
    s = s.strip()
    if s.endswith("m"):
        return int(s[:-1]) / 1000.0
    return float(s)


def _parse_memory(s: str) -> int:
    s = s.strip().upper()
    if s.endswith("GI"):
        return int(s[:-2]) * 1024 * 1024 * 1024
    if s.endswith("MI"):
        return int(s[:-2]) * 1024 * 1024
    if s.endswith("KI"):
        return int(s[:-2]) * 1024
    if s.endswith("G"):
        return int(s[:-1]) * 1_000_000_000
    if s.endswith("M"):
        return int(s[:-1]) * 1_000_000
    if s.endswith("K"):
        return int(s[:-1]) * 1_000
    return int(s)


def _extract_scalar(data: dict) -> float:
    result = data.get("data", {}).get("result", [])
    if not result:
        return 0.0
    return float(result[0]["value"][1])

logger = logging.getLogger(__name__)


class WorkloadService:
    def __init__(self, repo: WorkloadRepository, k8s: K8sService, audit: AuditService) -> None:
        self._repo = repo
        self._k8s = k8s
        self._audit = audit

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
                container_port=w.container_port,
                ingress_host=w.ingress_host,
                env_vars=w.env_vars or {},
                cpu_limit=w.cpu_limit,
                memory_limit=w.memory_limit,
                liveness_path=w.liveness_path,
                readiness_path=w.readiness_path,
                status=w.status,
                created_at=w.created_at,
            ))
        return result

    async def create_workload(self, data: WorkloadCreate, actor: str = "system") -> WorkloadResponse:
        existing = await self._repo.get_by_name(data.name)
        if existing and existing.status != WorkloadStatus.DELETED:
            await self._audit.log("workload.create", "workload", data.name, actor, "failure", "Workload already exists")
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
                data.env_vars or None, data.cpu_limit, data.memory_limit,
                data.liveness_path, data.readiness_path, data.container_port,
            )
        except ApiException as e:
            await self._audit.log("workload.create", "workload", data.name, actor, "failure", e.reason)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")

        ingress_host = None
        if data.container_port:
            ingress_host = data.ingress_host or f"{data.name}.pi-cluster.local"
            try:
                await run_in_threadpool(
                    self._k8s.create_service, data.name, data.namespace, data.container_port
                )
                await run_in_threadpool(
                    self._k8s.create_ingress, data.name, data.namespace, ingress_host, data.container_port
                )
            except ApiException as e:
                logger.warning("Service/Ingress creation failed for %s: %s", data.name, e.reason)
                ingress_host = None

        resolved = data.model_copy(update={"target_node": target_node, "ingress_host": ingress_host})
        workload = await self._repo.create(resolved)
        await self._repo.update_status(workload.name, WorkloadStatus.RUNNING)

        detail = f"node={target_node or 'auto'} image={data.image}"
        if ingress_host:
            detail += f" ingress={ingress_host}"
        await self._audit.log("workload.create", "workload", workload.name, actor, "success", detail)

        return WorkloadResponse(
            id=workload.id,
            name=workload.name,
            namespace=workload.namespace,
            image=workload.image,
            replicas=workload.replicas,
            ready_replicas=0,
            target_node=workload.target_node,
            container_port=workload.container_port,
            ingress_host=workload.ingress_host,
            env_vars=workload.env_vars or {},
            cpu_limit=workload.cpu_limit,
            memory_limit=workload.memory_limit,
            liveness_path=workload.liveness_path,
            readiness_path=workload.readiness_path,
            status=WorkloadStatus.RUNNING,
            created_at=workload.created_at,
        )

    async def delete_workload(self, name: str, actor: str = "system") -> None:
        workload = await self._repo.get_by_name(name)
        if workload is None or workload.status == WorkloadStatus.DELETED:
            await self._audit.log("workload.delete", "workload", name, actor, "failure", "Workload not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workload not found")

        try:
            await run_in_threadpool(self._k8s.delete_deployment, name, workload.namespace)
        except ApiException as e:
            if e.status != 404:
                await self._audit.log("workload.delete", "workload", name, actor, "failure", e.reason)
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")

        if workload.container_port:
            for fn in (self._k8s.delete_ingress, self._k8s.delete_service):
                try:
                    await run_in_threadpool(fn, name, workload.namespace)
                except ApiException as e:
                    if e.status != 404:
                        logger.warning("Cleanup failed for %s: %s", name, e.reason)

        await self._repo.update_status(name, WorkloadStatus.DELETED)
        await self._audit.log("workload.delete", "workload", name, actor, "success")

    async def scale_workload(self, name: str, replicas: int, actor: str = "system") -> WorkloadResponse:
        workload = await self._repo.get_by_name(name)
        if workload is None or workload.status == WorkloadStatus.DELETED:
            await self._audit.log("workload.scale", "workload", name, actor, "failure", "Workload not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workload not found")

        try:
            await run_in_threadpool(self._k8s.scale_deployment, name, workload.namespace, replicas)
        except ApiException as e:
            await self._audit.log("workload.scale", "workload", name, actor, "failure", e.reason)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")

        workload = await self._repo.update_replicas(name, replicas)
        await self._audit.log("workload.scale", "workload", name, actor, "success", f"replicas={replicas}")

        return WorkloadResponse(
            id=workload.id,
            name=workload.name,
            namespace=workload.namespace,
            image=workload.image,
            replicas=workload.replicas,
            ready_replicas=0,
            target_node=workload.target_node,
            container_port=workload.container_port,
            ingress_host=workload.ingress_host,
            env_vars=workload.env_vars or {},
            cpu_limit=workload.cpu_limit,
            memory_limit=workload.memory_limit,
            liveness_path=workload.liveness_path,
            readiness_path=workload.readiness_path,
            status=workload.status,
            created_at=workload.created_at,
        )

    async def update_workload_image(self, name: str, image: str, actor: str = "system") -> WorkloadResponse:
        workload = await self._repo.get_by_name(name)
        if workload is None or workload.status == WorkloadStatus.DELETED:
            await self._audit.log("workload.update_image", "workload", name, actor, "failure", "Workload not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workload not found")

        try:
            await run_in_threadpool(self._k8s.update_deployment_image, name, workload.namespace, image)
        except ApiException as e:
            await self._audit.log("workload.update_image", "workload", name, actor, "failure", e.reason)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")

        workload = await self._repo.update_image(name, image)
        await self._audit.log("workload.update_image", "workload", name, actor, "success", f"image={image}")

        return WorkloadResponse(
            id=workload.id,
            name=workload.name,
            namespace=workload.namespace,
            image=workload.image,
            replicas=workload.replicas,
            ready_replicas=0,
            target_node=workload.target_node,
            container_port=workload.container_port,
            ingress_host=workload.ingress_host,
            env_vars=workload.env_vars or {},
            cpu_limit=workload.cpu_limit,
            memory_limit=workload.memory_limit,
            liveness_path=workload.liveness_path,
            readiness_path=workload.readiness_path,
            status=workload.status,
            created_at=workload.created_at,
        )

    async def update_workload_env(self, name: str, env_vars: dict[str, str], actor: str = "system") -> WorkloadResponse:
        workload = await self._repo.get_by_name(name)
        if workload is None or workload.status == WorkloadStatus.DELETED:
            await self._audit.log("workload.update_env", "workload", name, actor, "failure", "Workload not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workload not found")

        try:
            await run_in_threadpool(self._k8s.update_deployment_env, name, workload.namespace, env_vars)
        except ApiException as e:
            await self._audit.log("workload.update_env", "workload", name, actor, "failure", e.reason)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")

        workload = await self._repo.update_env_vars(name, env_vars)
        await self._audit.log("workload.update_env", "workload", name, actor, "success", f"vars={list(env_vars.keys())}")

        return WorkloadResponse(
            id=workload.id,
            name=workload.name,
            namespace=workload.namespace,
            image=workload.image,
            replicas=workload.replicas,
            ready_replicas=0,
            target_node=workload.target_node,
            container_port=workload.container_port,
            ingress_host=workload.ingress_host,
            env_vars=workload.env_vars or {},
            cpu_limit=workload.cpu_limit,
            memory_limit=workload.memory_limit,
            liveness_path=workload.liveness_path,
            readiness_path=workload.readiness_path,
            status=workload.status,
            created_at=workload.created_at,
        )

    async def update_workload_resources(self, name: str, cpu_limit: str, memory_limit: str, actor: str = "system") -> WorkloadResponse:
        workload = await self._repo.get_by_name(name)
        if workload is None or workload.status == WorkloadStatus.DELETED:
            await self._audit.log("workload.update_resources", "workload", name, actor, "failure", "Workload not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workload not found")

        try:
            await run_in_threadpool(self._k8s.update_deployment_resources, name, workload.namespace, cpu_limit, memory_limit)
        except ApiException as e:
            await self._audit.log("workload.update_resources", "workload", name, actor, "failure", e.reason)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")

        workload = await self._repo.update_resources(name, cpu_limit, memory_limit)
        await self._audit.log("workload.update_resources", "workload", name, actor, "success", f"cpu_limit={cpu_limit} memory_limit={memory_limit}")

        return WorkloadResponse(
            id=workload.id,
            name=workload.name,
            namespace=workload.namespace,
            image=workload.image,
            replicas=workload.replicas,
            ready_replicas=0,
            target_node=workload.target_node,
            container_port=workload.container_port,
            ingress_host=workload.ingress_host,
            env_vars=workload.env_vars or {},
            cpu_limit=workload.cpu_limit,
            memory_limit=workload.memory_limit,
            liveness_path=workload.liveness_path,
            readiness_path=workload.readiness_path,
            status=workload.status,
            created_at=workload.created_at,
        )

    async def update_workload_probes(
        self, name: str, liveness_path: str | None, readiness_path: str | None, actor: str = "system"
    ) -> WorkloadResponse:
        workload = await self._repo.get_by_name(name)
        if workload is None or workload.status == WorkloadStatus.DELETED:
            await self._audit.log("workload.update_probes", "workload", name, actor, "failure", "Workload not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workload not found")

        if (liveness_path or readiness_path) and not workload.container_port:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Probes require a container port")

        try:
            await run_in_threadpool(
                self._k8s.update_deployment_probes,
                name, workload.namespace, liveness_path, readiness_path, workload.container_port or 0,
            )
        except ApiException as e:
            await self._audit.log("workload.update_probes", "workload", name, actor, "failure", e.reason)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")

        workload = await self._repo.update_probes(name, liveness_path, readiness_path)
        detail = f"liveness={liveness_path or 'none'} readiness={readiness_path or 'none'}"
        await self._audit.log("workload.update_probes", "workload", name, actor, "success", detail)

        return WorkloadResponse(
            id=workload.id,
            name=workload.name,
            namespace=workload.namespace,
            image=workload.image,
            replicas=workload.replicas,
            ready_replicas=0,
            target_node=workload.target_node,
            container_port=workload.container_port,
            ingress_host=workload.ingress_host,
            env_vars=workload.env_vars or {},
            cpu_limit=workload.cpu_limit,
            memory_limit=workload.memory_limit,
            liveness_path=workload.liveness_path,
            readiness_path=workload.readiness_path,
            status=workload.status,
            created_at=workload.created_at,
        )

    async def restart_workload(self, name: str, actor: str = "system") -> None:
        workload = await self._repo.get_by_name(name)
        if workload is None or workload.status == WorkloadStatus.DELETED:
            await self._audit.log("workload.restart", "workload", name, actor, "failure", "Workload not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workload not found")

        try:
            await run_in_threadpool(self._k8s.restart_deployment, name, workload.namespace)
        except ApiException as e:
            await self._audit.log("workload.restart", "workload", name, actor, "failure", e.reason)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")

        await self._audit.log("workload.restart", "workload", name, actor, "success")

    async def get_workload_events(self, name: str) -> list[WorkloadEvent]:
        workload = await self._repo.get_by_name(name)
        if workload is None or workload.status == WorkloadStatus.DELETED:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workload not found")
        try:
            raw = await run_in_threadpool(self._k8s.get_workload_events, name, workload.namespace)
        except ApiException as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")
        return [
            WorkloadEvent(
                type=e.type or "Normal",
                reason=e.reason or "",
                message=e.message or "",
                object_name=e.involved_object.name or "",
                count=e.count or 1,
                first_time=e.first_timestamp,
                last_time=e.last_timestamp,
            )
            for e in raw
        ]

    async def get_workload_pods(self, name: str) -> list[PodInfo]:
        workload = await self._repo.get_by_name(name)
        if workload is None or workload.status == WorkloadStatus.DELETED:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workload not found")
        try:
            pods = await run_in_threadpool(self._k8s.get_pod_list, name, workload.namespace)
        except ApiException as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")
        return [
            PodInfo(
                name=p.metadata.name,
                phase=p.status.phase or "Unknown",
                node=p.spec.node_name,
                pod_ip=p.status.pod_ip,
                ready=sum(1 for cs in (p.status.container_statuses or []) if cs.ready),
                total=len(p.spec.containers),
                started_at=p.status.start_time,
            )
            for p in pods
        ]

    async def get_workload_logs(self, name: str, tail_lines: int = 100) -> WorkloadLogs:
        workload = await self._repo.get_by_name(name)
        if workload is None or workload.status == WorkloadStatus.DELETED:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workload not found")
        try:
            pod_name, logs = await run_in_threadpool(
                self._k8s.get_pod_logs, name, workload.namespace, tail_lines
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ApiException as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")
        return WorkloadLogs(name=name, pod_name=pod_name, logs=logs)

    async def get_node_capacities(self) -> list[NodeCapacity]:
        try:
            return await run_in_threadpool(self._k8s.get_node_capacities)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e}")

    async def cordon_node(self, node_name: str, actor: str = "system") -> None:
        try:
            await run_in_threadpool(self._k8s.cordon_node, node_name)
        except ApiException as e:
            await self._audit.log("node.cordon", "node", node_name, actor, "failure", e.reason)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")
        await self._audit.log("node.cordon", "node", node_name, actor, "success")

    async def uncordon_node(self, node_name: str, actor: str = "system") -> None:
        try:
            await run_in_threadpool(self._k8s.uncordon_node, node_name)
        except ApiException as e:
            await self._audit.log("node.uncordon", "node", node_name, actor, "failure", e.reason)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")
        await self._audit.log("node.uncordon", "node", node_name, actor, "success")

    async def drain_node(self, node_name: str, actor: str = "system") -> int:
        try:
            evicted = await run_in_threadpool(self._k8s.drain_node, node_name)
        except ApiException as e:
            await self._audit.log("node.drain", "node", node_name, actor, "failure", e.reason)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")
        await self._audit.log("node.drain", "node", node_name, actor, "success", f"evicted={evicted}")
        return evicted

    async def get_workload_metrics(self, name: str) -> WorkloadMetrics:
        workload = await self._repo.get_by_name(name)
        if workload is None or workload.status == WorkloadStatus.DELETED:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workload not found")

        cpu_limit_cores = _parse_cpu(workload.cpu_limit or "500m")
        memory_limit_bytes = _parse_memory(workload.memory_limit or "256Mi")

        cpu_cores = 0.0
        memory_bytes = 0
        available = False
        try:
            cpu_q = (
                f'sum(rate(container_cpu_usage_seconds_total'
                f'{{pod=~"{name}-.*",container!="",container!="POD"}}[5m]))'
            )
            mem_q = (
                f'sum(container_memory_working_set_bytes'
                f'{{pod=~"{name}-.*",container!="",container!="POD"}})'
            )
            async with httpx.AsyncClient(timeout=5.0) as client:
                cpu_resp, mem_resp = await asyncio_gather(
                    client.get(f"{settings.prometheus_url}/api/v1/query", params={"query": cpu_q}),
                    client.get(f"{settings.prometheus_url}/api/v1/query", params={"query": mem_q}),
                )
            cpu_cores = _extract_scalar(cpu_resp.json())
            memory_bytes = int(_extract_scalar(mem_resp.json()))
            available = True
        except Exception as e:
            logger.warning("Prometheus query failed for workload %s: %s", name, e)

        try:
            pods = await run_in_threadpool(self._k8s.get_pod_list, name, workload.namespace)
            pod_count = len(pods)
        except Exception:
            pod_count = 0

        return WorkloadMetrics(
            name=name,
            cpu_cores=cpu_cores,
            cpu_limit_cores=cpu_limit_cores,
            memory_bytes=memory_bytes,
            memory_limit_bytes=memory_limit_bytes,
            pod_count=pod_count,
            available=available,
        )

    async def get_workload_history(self, name: str) -> WorkloadHistory:
        workload = await self._repo.get_by_name(name)
        if workload is None or workload.status == WorkloadStatus.DELETED:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workload not found")
        try:
            raw = await run_in_threadpool(self._k8s.get_rollout_history, name, workload.namespace)
        except ApiException as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")
        revisions = [
            DeploymentRevision(
                revision=r["revision"],
                image=r["image"],
                created_at=r["created_at"],
                is_current=r["is_current"],
            )
            for r in raw
        ]
        return WorkloadHistory(name=name, revisions=revisions)

    async def rollback_workload(self, name: str, revision: int, actor: str = "system") -> WorkloadResponse:
        workload = await self._repo.get_by_name(name)
        if workload is None or workload.status == WorkloadStatus.DELETED:
            await self._audit.log("workload.rollback", "workload", name, actor, "failure", "Workload not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workload not found")
        try:
            rolled_back_image = await run_in_threadpool(
                self._k8s.rollback_deployment, name, workload.namespace, revision
            )
        except ValueError as e:
            await self._audit.log("workload.rollback", "workload", name, actor, "failure", str(e))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ApiException as e:
            await self._audit.log("workload.rollback", "workload", name, actor, "failure", e.reason)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"K8s: {e.reason}")

        workload = await self._repo.update_image(name, rolled_back_image)
        await self._audit.log(
            "workload.rollback", "workload", name, actor, "success",
            f"revision={revision} image={rolled_back_image}"
        )
        return WorkloadResponse(
            id=workload.id,
            name=workload.name,
            namespace=workload.namespace,
            image=workload.image,
            replicas=workload.replicas,
            ready_replicas=0,
            target_node=workload.target_node,
            container_port=workload.container_port,
            ingress_host=workload.ingress_host,
            env_vars=workload.env_vars or {},
            cpu_limit=workload.cpu_limit,
            memory_limit=workload.memory_limit,
            liveness_path=workload.liveness_path,
            readiness_path=workload.readiness_path,
            status=workload.status,
            created_at=workload.created_at,
        )
