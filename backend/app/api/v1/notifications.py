from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.database import get_db
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import ChannelCreate, ChannelResponse, ChannelUpdate
from app.services.notification_service import test_channel

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/channels", response_model=list[ChannelResponse])
async def list_channels(
    db: AsyncSession = Depends(get_db), _=Depends(require_admin)
) -> list[ChannelResponse]:
    return await NotificationRepository(db).list_all()  # type: ignore[return-value]


@router.post("/channels", response_model=ChannelResponse, status_code=201)
async def create_channel(
    body: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
) -> ChannelResponse:
    if body.channel_type == "email" and not body.email_address:
        raise HTTPException(status_code=422, detail="email_address is required for type=email")
    if body.channel_type == "webhook" and not body.url:
        raise HTTPException(status_code=422, detail="url is required for type=webhook")
    return await NotificationRepository(db).create(  # type: ignore[return-value]
        name=body.name,
        channel_type=body.channel_type,
        url=body.url,
        email_address=body.email_address,
        enabled=body.enabled,
    )


@router.patch("/channels/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: int,
    body: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
) -> ChannelResponse:
    repo = NotificationRepository(db)
    ch = await repo.get_by_id(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    return await repo.update(ch, **body.model_dump(exclude_none=True))  # type: ignore[return-value]


@router.delete("/channels/{channel_id}", status_code=204)
async def delete_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
) -> None:
    repo = NotificationRepository(db)
    ch = await repo.get_by_id(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    await repo.delete(ch)


@router.post("/channels/{channel_id}/test")
async def test_channel_endpoint(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
) -> dict[str, bool]:
    repo = NotificationRepository(db)
    ch = await repo.get_by_id(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    ok = await test_channel(ch)
    return {"ok": ok}
