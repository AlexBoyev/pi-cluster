import logging

from app.repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, repo: AuditRepository) -> None:
        self._repo = repo

    async def log(
        self,
        action: str,
        resource_type: str,
        resource_name: str,
        actor: str,
        status: str,
        detail: str | None = None,
    ) -> None:
        try:
            await self._repo.create(action, resource_type, resource_name, actor, status, detail)
        except Exception as e:
            logger.error("Audit log write failed: %s", e)
