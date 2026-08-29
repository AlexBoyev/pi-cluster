from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.alert_history_repository import AlertHistoryRepository
from app.schemas.alert_history import AlertHistoryEntry

router = APIRouter(prefix="/alert-history", tags=["alert-history"])


@router.get("/", response_model=list[AlertHistoryEntry])
async def list_alert_history(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    severity: str | None = Query(None),
    state: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[AlertHistoryEntry]:
    return await AlertHistoryRepository(db).get_recent(
        limit=limit, offset=offset, severity=severity, state=state
    )
