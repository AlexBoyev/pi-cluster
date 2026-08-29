import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from unittest.mock import AsyncMock, MagicMock, patch

# Override settings BEFORE importing the app
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-only")
os.environ.setdefault("ADMIN_DEFAULT_PASSWORD", "adminpass123")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SSH_USERNAME", "pi")
os.environ.setdefault("SSH_PASSWORD", "test")
os.environ.setdefault("K8S_KUBECONFIG_PATH", "/tmp/test-kubeconfig.yaml")
os.environ.setdefault("PROMETHEUS_URL", "http://localhost:9090")

from app.main import app
from app.database import Base, engine, get_db, AsyncSessionLocal
from app.auth.service import hash_password, create_access_token
from app.models.user import UserRole
from app.repositories.user_repository import UserRepository

TEST_DB_URL = "sqlite+aiosqlite:///./test_ci.db"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_session_factory(test_engine):
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
async def admin_token(test_session_factory):
    async with test_session_factory() as db:
        repo = UserRepository(db)
        existing = await repo.get_by_username("admin")
        if existing is None:
            await repo.create(
                username="admin",
                hashed_password=hash_password("adminpass123"),
                role=UserRole.ADMIN,
            )
    token = create_access_token("admin", "admin")
    return token


@pytest_asyncio.fixture(scope="session")
async def viewer_token(test_session_factory):
    async with test_session_factory() as db:
        repo = UserRepository(db)
        existing = await repo.get_by_username("testviewer")
        if existing is None:
            await repo.create(
                username="testviewer",
                hashed_password=hash_password("Viewpass1!"),
                role=UserRole.VIEWER,
            )
    token = create_access_token("testviewer", "viewer")
    return token


@pytest_asyncio.fixture(scope="session")
async def client(test_session_factory, admin_token, viewer_token):
    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Use AsyncMock so that the patched coroutines never actually run
    with patch(
        "app.services.health_service.poll_health_forever",
        new_callable=AsyncMock,
    ):
        with patch(
            "app.services.alert_history_service.poll_alert_history_forever",
            new_callable=AsyncMock,
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                yield c

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def viewer_headers(viewer_token):
    return {"Authorization": f"Bearer {viewer_token}"}
