import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import require_admin
from app.config import settings
from app.schemas.alert_rule import AlertRuleCreate, AlertRuleUpdate
from app.services.alert_rules_service import AlertRuleError, alert_rules_service

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


@router.post("/rules", status_code=201)
async def create_rule(body: AlertRuleCreate, _=Depends(require_admin)) -> dict:
    try:
        await alert_rules_service.create_rule(
            body.group, body.alert, body.expr, body.for_,
            body.severity, body.summary, body.description,
        )
    except AlertRuleError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"detail": "Rule created and published"}


@router.patch("/rules/{group}/{alert}")
async def update_rule(
    group: str, alert: str, body: AlertRuleUpdate, _=Depends(require_admin)
) -> dict:
    try:
        await alert_rules_service.update_rule(
            group, alert, body.expr, body.for_, body.severity, body.summary, body.description
        )
    except AlertRuleError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"detail": "Rule updated and published"}


@router.delete("/rules/{group}/{alert}")
async def delete_rule(group: str, alert: str, _=Depends(require_admin)) -> dict:
    try:
        await alert_rules_service.delete_rule(group, alert)
    except AlertRuleError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"detail": "Rule deleted and published"}
