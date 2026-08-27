from fastapi import APIRouter

from app.api.v1 import nodes

router = APIRouter(prefix="/api/v1")
router.include_router(nodes.router)
