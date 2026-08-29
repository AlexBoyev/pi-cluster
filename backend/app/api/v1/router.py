from fastapi import APIRouter, Depends

from app.api.v1 import alert_history, alerts, audit, auth, cluster, configmaps, cronjobs, events, exec, helm, health, jobs, namespaces, nodes, notifications, objects, pods, prom_rules, quotas, rbac, secrets, services, storage, users, workloads
from app.auth.dependencies import require_admin

router = APIRouter(prefix="/api/v1")

# Public
router.include_router(auth.router)

# WebSocket exec — auth handled inside the endpoint via ?token= query param
router.include_router(exec.router)

# Admin only — all cluster management and infrastructure
router.include_router(nodes.router, dependencies=[Depends(require_admin)])
router.include_router(health.router, dependencies=[Depends(require_admin)])
router.include_router(workloads.router, dependencies=[Depends(require_admin)])
router.include_router(audit.router, dependencies=[Depends(require_admin)])
router.include_router(alerts.router, dependencies=[Depends(require_admin)])
router.include_router(alert_history.router, dependencies=[Depends(require_admin)])
router.include_router(cluster.router, dependencies=[Depends(require_admin)])
router.include_router(events.router, dependencies=[Depends(require_admin)])
router.include_router(namespaces.router, dependencies=[Depends(require_admin)])
router.include_router(users.router, dependencies=[Depends(require_admin)])
router.include_router(configmaps.router, dependencies=[Depends(require_admin)])
router.include_router(secrets.router, dependencies=[Depends(require_admin)])
router.include_router(services.router, dependencies=[Depends(require_admin)])
router.include_router(cronjobs.router, dependencies=[Depends(require_admin)])
router.include_router(storage.router, dependencies=[Depends(require_admin)])
router.include_router(notifications.router, dependencies=[Depends(require_admin)])
router.include_router(objects.router, dependencies=[Depends(require_admin)])
router.include_router(helm.router, dependencies=[Depends(require_admin)])
router.include_router(rbac.router, dependencies=[Depends(require_admin)])
router.include_router(pods.router, dependencies=[Depends(require_admin)])
router.include_router(jobs.router, dependencies=[Depends(require_admin)])
router.include_router(quotas.router, dependencies=[Depends(require_admin)])
router.include_router(prom_rules.router, dependencies=[Depends(require_admin)])
