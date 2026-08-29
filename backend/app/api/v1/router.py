from fastapi import APIRouter, Depends

from app.api.v1 import alert_history, alerts, audit, auth, cluster, configmaps, cronjobs, events, exec, helm, health, jobs, namespaces, nodes, notifications, objects, pods, prom_rules, quotas, rbac, secrets, services, storage, users, workloads
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/v1")

# Public
router.include_router(auth.router)

# WebSocket exec — auth handled inside the endpoint via ?token= query param
router.include_router(exec.router)

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
router.include_router(secrets.router, dependencies=[Depends(get_current_user)])
router.include_router(services.router, dependencies=[Depends(get_current_user)])
router.include_router(cronjobs.router, dependencies=[Depends(get_current_user)])
router.include_router(storage.router, dependencies=[Depends(get_current_user)])
router.include_router(notifications.router, dependencies=[Depends(get_current_user)])
router.include_router(objects.router, dependencies=[Depends(get_current_user)])
router.include_router(helm.router, dependencies=[Depends(get_current_user)])
router.include_router(rbac.router, dependencies=[Depends(get_current_user)])
router.include_router(pods.router, dependencies=[Depends(get_current_user)])
router.include_router(jobs.router, dependencies=[Depends(get_current_user)])
router.include_router(quotas.router, dependencies=[Depends(get_current_user)])
router.include_router(prom_rules.router, dependencies=[Depends(get_current_user)])
