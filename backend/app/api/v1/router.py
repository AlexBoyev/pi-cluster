from fastapi import APIRouter

from app.api.v1 import health, nodes

router = APIRouter(prefix="/api/v1")
router.include_router(nodes.router)
router.include_router(health.router)
