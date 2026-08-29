import logging

import httpx
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.schemas.cluster import ClusterCapacity, NodeCapacityDetail
from app.services.k8s_service import K8sService

logger = logging.getLogger(__name__)


async def get_cluster_capacity() -> ClusterCapacity:
    k8s = K8sService()
    node_caps = await run_in_threadpool(k8s.get_node_capacities)

    mem_used_map: dict[str, int] = {}
    cpu_frac_map: dict[str, float] = {}

    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            mem_resp = await http.get(
                f"{settings.prometheus_url}/api/v1/query",
                params={"query": "node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes"},
            )
            if mem_resp.status_code == 200:
                for r in mem_resp.json().get("data", {}).get("result", []):
                    n = r.get("metric", {}).get("node_name")
                    if n:
                        mem_used_map[n] = int(float(r["value"][1]))

            cpu_resp = await http.get(
                f"{settings.prometheus_url}/api/v1/query",
                params={"query": '1 - avg by (node_name) (rate(node_cpu_seconds_total{mode="idle"}[5m]))'},
            )
            if cpu_resp.status_code == 200:
                for r in cpu_resp.json().get("data", {}).get("result", []):
                    n = r.get("metric", {}).get("node_name")
                    if n:
                        cpu_frac_map[n] = float(r["value"][1])
    except Exception as e:
        logger.warning("Prometheus unreachable for cluster capacity: %s", e)

    nodes: list[NodeCapacityDetail] = []
    total_cpu_alloc = total_cpu_req = total_cpu_used = 0.0
    total_mem_alloc = total_mem_req = total_mem_used = 0

    for nc in node_caps:
        cpu_alloc = nc.cpu_allocatable_m / 1000.0
        cpu_req   = nc.cpu_requested_m / 1000.0
        mem_alloc = nc.memory_allocatable_mi * 1024 * 1024
        mem_req   = nc.memory_requested_mi * 1024 * 1024
        cpu_used  = cpu_frac_map.get(nc.node_name, 0.0) * cpu_alloc
        mem_used  = mem_used_map.get(nc.node_name, 0)

        nodes.append(NodeCapacityDetail(
            node_name=nc.node_name,
            cpu_allocatable_cores=round(cpu_alloc, 3),
            cpu_requested_cores=round(cpu_req, 3),
            cpu_used_cores=round(cpu_used, 3),
            memory_allocatable_bytes=mem_alloc,
            memory_requested_bytes=mem_req,
            memory_used_bytes=mem_used,
            ready=nc.ready,
            schedulable=nc.schedulable,
        ))
        total_cpu_alloc += cpu_alloc
        total_cpu_req   += cpu_req
        total_cpu_used  += cpu_used
        total_mem_alloc += mem_alloc
        total_mem_req   += mem_req
        total_mem_used  += mem_used

    return ClusterCapacity(
        cpu_allocatable_cores=round(total_cpu_alloc, 3),
        cpu_requested_cores=round(total_cpu_req, 3),
        cpu_used_cores=round(total_cpu_used, 3),
        memory_allocatable_bytes=total_mem_alloc,
        memory_requested_bytes=total_mem_req,
        memory_used_bytes=total_mem_used,
        nodes=sorted(nodes, key=lambda n: n.node_name),
    )
