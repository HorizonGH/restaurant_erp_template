from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.core.shared.infrastructure.repository import BaseRepository
from app.modules.waste.domain.models import WasteCategory, WasteRecord


class WasteCategoryRepository(BaseRepository[WasteCategory]):
    model = WasteCategory

    async def get_by_name(self, name: str) -> WasteCategory | None:
        result = await self.session.execute(
            select(WasteCategory).where(
                WasteCategory.name == name,
                WasteCategory.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def has_records(self, category_id: UUID) -> bool:
        result = await self.session.execute(
            select(WasteRecord).where(
                WasteRecord.waste_category_id == category_id,
                WasteRecord.is_deleted.is_(False),
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None


class WasteRecordRepository(BaseRepository[WasteRecord]):
    model = WasteRecord

    async def list_by_ingredient(self, ingredient_id: UUID) -> list[WasteRecord]:
        result = await self.session.execute(
            select(WasteRecord).where(
                WasteRecord.ingredient_id == ingredient_id,
                WasteRecord.is_deleted.is_(False),
            ).order_by(WasteRecord.waste_date.desc())
        )
        return list(result.scalars().all())

    async def list_by_location(self, location_id: UUID) -> list[WasteRecord]:
        result = await self.session.execute(
            select(WasteRecord).where(
                WasteRecord.location_id == location_id,
                WasteRecord.is_deleted.is_(False),
            ).order_by(WasteRecord.waste_date.desc())
        )
        return list(result.scalars().all())
