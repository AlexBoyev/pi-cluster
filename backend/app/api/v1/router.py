from fastapi import APIRouter, Depends

from app.api.v1 import alerts, audit, auth, health, nodes, workloads
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
