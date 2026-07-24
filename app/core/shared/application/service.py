from collections.abc import Sequence
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.domain.entities import BaseEntity
from app.core.shared.infrastructure.filters import AsyncFilterSet
from app.core.shared.infrastructure.repository import BaseRepository

EntityT = TypeVar("EntityT", bound=BaseEntity)


class BaseService(Generic[EntityT]):
    repository_cls: type[BaseRepository[EntityT]]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = self.repository_cls(session)

    async def get(self, id: UUID) -> EntityT:
        return await self.repository.get_or_404(id)

    async def list(
        self, filterset_cls: type[AsyncFilterSet[EntityT]], params: dict[str, Any]
    ) -> tuple[Sequence[EntityT], int]:
        return await self.repository.list(filterset_cls, params)

    async def create(self, **values: Any) -> EntityT:
        obj = await self.repository.create(**values)
        await self.session.commit()
        return obj

    async def update(self, id: UUID, **values: Any) -> EntityT:
        obj = await self.repository.get_or_404(id)
        obj = await self.repository.update(obj, **values)
        await self.session.commit()
        return obj

    async def delete(self, id: UUID) -> None:
        obj = await self.repository.get_or_404(id)
        await self.repository.delete(obj)
        await self.session.commit()
