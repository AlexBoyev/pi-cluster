from fastapi import APIRouter

from app.schemas.alert import AlertResponse
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/", response_model=list[AlertResponse])
async def list_alerts() -> list[AlertResponse]:
    return await AlertService().get_alerts()
