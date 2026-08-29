from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from app.schemas.k8s_event import ClusterEvent
from app.services.k8s_service import K8sService

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=list[ClusterEvent])
async def list_cluster_events(
    namespace: str | None = Query(None),
    event_type: str | None = Query(None),
    limit: int = Query(200, ge=1, le=500),
) -> list[ClusterEvent]:
    k8s = K8sService()
    raw = await run_in_threadpool(k8s.get_cluster_events, namespace, event_type, limit)
    return [ClusterEvent(**e) for e in raw]
