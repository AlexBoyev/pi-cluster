import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.router import router

logger = logging.getLogger(__name__)


async def _seed_admin() -> None:
    from app.auth.service import hash_password
    from app.config import settings
    from app.database import AsyncSessionLocal
    from app.models.user import UserRole
    from app.repositories.user_repository import UserRepository

    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)
        if await repo.count() == 0:
            await repo.create(
                username="admin",
                hashed_password=hash_password(settings.admin_default_password),
                role=UserRole.ADMIN,
            )
            logger.warning(
                "Created default admin user. Change the password via ADMIN_DEFAULT_PASSWORD env var."
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.alert_history_service import poll_alert_history_forever
    from app.services.health_service import poll_health_forever
    await _seed_admin()
    health_task = asyncio.create_task(poll_health_forever())
    alert_task = asyncio.create_task(poll_alert_history_forever())
    yield
    health_task.cancel()
    alert_task.cancel()
    for t in (health_task, alert_task):
        try:
            await t
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Pi-Cluster API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://10.100.102.10:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
