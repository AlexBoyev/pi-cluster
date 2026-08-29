from fastapi import APIRouter, Depends

from app.api.v1 import alert_history, alerts, audit, auth, cluster, configmaps, events, health, namespaces, nodes, users, workloads
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/v1")

# Public
router.include_router(auth.router)

# Protected — any authenticated user
router.include_router(nodes.router, dependencies=[Depends(get_current_user)])
router.include_router(health.router, dependencies=[Depends(get_current_user)])
router.include_router(workloads.router, dependencies=[Depends(get_current_user)])
router.include_router(audit.router, dependencies=[Depends(get_current_user)])
router.include_router(alerts.router, dependencies=[Depends(get_current_user)])
router.include_router(alert_history.router, dependencies=[Depends(get_current_user)])
router.include_router(cluster.router, dependencies=[Depends(get_current_user)])
router.include_router(events.router, dependencies=[Depends(get_current_user)])
router.include_router(namespaces.router, dependencies=[Depends(get_current_user)])
router.include_router(users.router, dependencies=[Depends(get_current_user)])
router.include_router(configmaps.router, dependencies=[Depends(get_current_user)])
