import asyncio
import logging
from datetime import datetime, timezone

from app.cache import redis_client
from app.database import AsyncSessionLocal
from app.models.node import NodeStatus
from app.repositories.node_repository import NodeRepository
from app.schemas.health import NodeHealthResponse, NodeMetrics
from app.services.ssh_service import ssh_service

logger = logging.getLogger(__name__)

CACHE_TTL = 90       # seconds before a cached result is considered stale
POLL_INTERVAL = 30   # seconds between full-cluster health sweeps


class HealthService:
    def __init__(self, repo: NodeRepository) -> None:
        self._repo = repo

    async def check_node(self, node_id: int) -> NodeHealthResponse | None:
        node = await self._repo.get_by_id(node_id)
        if node is None:
            return None

        checked_at = datetime.now(timezone.utc)
        try:
            raw = await ssh_service.collect_metrics(node.ip_address)
            mem_total = raw["memory_total"]
            mem_avail = raw["memory_available"]
            disk_total = raw["disk_total"]
            disk_used = raw["disk_used"]
            metrics = NodeMetrics(
                cpu_load_1m=raw["load_1m"],
                memory_total_bytes=mem_total,
                memory_available_bytes=mem_avail,
                memory_percent=round(100 * (mem_total - mem_avail) / mem_total, 1) if mem_total else 0.0,
                disk_total_bytes=disk_total,
                disk_used_bytes=disk_used,
                disk_percent=round(100 * disk_used / disk_total, 1) if disk_total else 0.0,
                uptime_seconds=raw["uptime_seconds"],
                temperature_celsius=raw.get("temperature_celsius"),
            )
            new_status = NodeStatus.ONLINE
            error = None
        except Exception as exc:
            logger.warning("health check failed for %s (%s): %s", node.name, node.ip_address, exc)
            metrics = None
            new_status = NodeStatus.OFFLINE
            error = str(exc)

        if node.status != new_status:
            await self._repo.update_status(node.id, new_status)

        result = NodeHealthResponse(
            node_id=node.id,
            node_name=node.name,
            ip_address=node.ip_address,
            status=new_status,
            metrics=metrics,
            checked_at=checked_at,
            error=error,
        )
        await redis_client.setex(f"node:{node.id}:health", CACHE_TTL, result.model_dump_json())
        return result

    async def get_cached(self, node_id: int) -> NodeHealthResponse | None:
        data = await redis_client.get(f"node:{node_id}:health")
        return NodeHealthResponse.model_validate_json(data) if data else None

    async def get_or_check(self, node_id: int) -> NodeHealthResponse | None:
        cached = await self.get_cached(node_id)
        return cached if cached is not None else await self.check_node(node_id)

    async def check_all(self) -> list[NodeHealthResponse]:
        nodes = await self._repo.get_all()
        results = await asyncio.gather(
            *[self.check_node(n.id) for n in nodes], return_exceptions=True
        )
        return [r for r in results if isinstance(r, NodeHealthResponse)]


async def poll_health_forever() -> None:
    """Background task: poll all nodes on a fixed interval."""
    while True:
        try:
            async with AsyncSessionLocal() as session:
                service = HealthService(NodeRepository(session))
                await service.check_all()
        except Exception:
            logger.exception("health poll cycle failed")
        await asyncio.sleep(POLL_INTERVAL)
