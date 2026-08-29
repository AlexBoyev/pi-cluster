import httpx
from fastapi import APIRouter, HTTPException

from app.config import settings

router = APIRouter(prefix="/prometheus", tags=["prometheus"])


@router.get("/rules")
async def get_alert_rules() -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.prometheus_url}/api/v1/rules",
                params={"type": "alert"},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Prometheus unreachable: {e}")
