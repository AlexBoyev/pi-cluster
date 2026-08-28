import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WorkloadStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    FAILED = "failed"
    DELETED = "deleted"


class Workload(Base):
    __tablename__ = "workloads"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    namespace: Mapped[str] = mapped_column(String(64), nullable=False)
    image: Mapped[str] = mapped_column(String(255), nullable=False)
    replicas: Mapped[int] = mapped_column(Integer, nullable=False)
    target_node: Mapped[str | None] = mapped_column(String(64), nullable=True)
    container_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ingress_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    env_vars: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    status: Mapped[WorkloadStatus] = mapped_column(
        Enum(WorkloadStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=WorkloadStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
