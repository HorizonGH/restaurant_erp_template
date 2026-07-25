import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.shared.domain.helpers import utcnow
from app.core.shared.infrastructure.database import Base


class UUIDMixin:
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)


class BaseEntity(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __abstract__ = True
