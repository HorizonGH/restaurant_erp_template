from collections.abc import Sequence
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.domain.entities import BaseEntity
from app.core.shared.domain.exceptions import NotFoundException
from app.core.shared.infrastructure.filters import AsyncFilterSet


EntityT = TypeVar("EntityT", bound=BaseEntity)


class BaseRepository(Generic[EntityT]):
    model: type[EntityT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id: UUID) -> EntityT | None:
        return await self.session.get(self.model, id)

    async def get_or_404(self, id: UUID) -> EntityT:
        obj = await self.get(id)
        if obj is None:
            raise NotFoundException(f"{self.model.__name__} not found")
        return obj

    async def list(
        self, filterset_cls: type[AsyncFilterSet[EntityT]], params: dict[str, Any]
    ) -> tuple[Sequence[EntityT], int]:
        filterset = filterset_cls(self.session, select(self.model))
        items = await filterset.filter(params)
        total = await filterset.count(params)
        return items, total

    async def create(self, **values: Any) -> EntityT:
        obj = self.model(**values)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def update(self, obj: EntityT, **values: Any) -> EntityT:
        for key, value in values.items():
            setattr(obj, key, value)
        await self.session.flush()
        return obj

    async def delete(self, obj: EntityT) -> None:
        await self.session.delete(obj)
        await self.session.flush()
