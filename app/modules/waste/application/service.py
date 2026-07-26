from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.domain.exceptions import ConflictException
from app.modules.catalog.infrastructure.repository import IngredientRepository
from app.modules.inventory.application.schemas import MovementExitInput
from app.modules.inventory.application.service import MovementService
from app.modules.inventory.domain.enums import MovementType
from app.modules.inventory.infrastructure.repository import (
    KardexRepository,
    LocationRepository,
)
from app.modules.waste.application.schemas import (
    WasteCategoryCreateInput,
    WasteCategoryUpdateInput,
    WasteRecordCreateInput,
    WasteSummaryLineOutput,
)
from app.modules.waste.domain.exceptions import WasteCategoryInUseException
from app.modules.waste.domain.models import WasteCategory, WasteRecord
from app.modules.waste.infrastructure.filters import (
    WasteCategoryFilterSet,
    WasteRecordFilterSet,
)
from app.modules.waste.infrastructure.repository import (
    WasteCategoryRepository,
    WasteRecordRepository,
)


class WasteCategoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = WasteCategoryRepository(session)

    async def get(self, category_id: UUID) -> WasteCategory:
        return await self.repo.get_or_404(category_id)

    async def list(self, params: dict) -> tuple[Sequence[WasteCategory], int]:
        return await self.repo.list(WasteCategoryFilterSet, params)

    async def list_all(self) -> list[WasteCategory]:
        result = await self.session.execute(
            select(WasteCategory).where(
                WasteCategory.is_deleted.is_(False)
            ).order_by(WasteCategory.name)
        )
        return list(result.scalars().all())

    async def create(self, data: WasteCategoryCreateInput) -> WasteCategory:
        existing = await self.repo.get_by_name(data.name)
        if existing is not None:
            raise ConflictException(f"Waste category '{data.name}' already exists")
        category = await self.repo.create(**data.model_dump())
        await self.session.commit()
        return category

    async def update(
        self, category_id: UUID, data: WasteCategoryUpdateInput
    ) -> WasteCategory:
        category = await self.repo.get_or_404(category_id)
        values = data.model_dump(exclude_none=True)
        if "name" in values:
            existing = await self.repo.get_by_name(values["name"])
            if existing is not None and existing.entity_id != category_id:
                raise ConflictException(
                    f"Waste category '{values['name']}' already exists"
                )
        category = await self.repo.update(category, **values)
        await self.session.commit()
        return category

    async def delete(self, category_id: UUID) -> None:
        category = await self.repo.get_or_404(category_id)
        if await self.repo.has_records(category_id):
            raise WasteCategoryInUseException(
                "Cannot delete a waste category that has waste records"
            )
        await self.repo.soft_delete(category)
        await self.session.commit()


class WasteRecordService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = WasteRecordRepository(session)
        self.category_repo = WasteCategoryRepository(session)
        self.ingredient_repo = IngredientRepository(session)
        self.location_repo = LocationRepository(session)
        self.kardex_repo = KardexRepository(session)
        self.movement_svc = MovementService(session)

    async def get(self, record_id: UUID) -> WasteRecord:
        return await self.repo.get_or_404(record_id)

    async def list(self, params: dict) -> tuple[Sequence[WasteRecord], int]:
        return await self.repo.list(WasteRecordFilterSet, params)

    async def record_waste(self, data: WasteRecordCreateInput) -> WasteRecord:
        """
        Records a waste event:
        1. Validates ingredient, location, and waste category exist.
        2. Fires an inventory exit movement of type `waste`.
        3. Creates a WasteRecord linking to that movement, storing the unit cost
           from the last kardex entry for audit trail.
        """
        await self.ingredient_repo.get_or_404(data.ingredient_id)
        await self.location_repo.get_or_404(data.location_id)
        await self.category_repo.get_or_404(data.waste_category_id)

        movement = await self.movement_svc.record_exit(
            MovementExitInput(
                ingredient_id=data.ingredient_id,
                location_id=data.location_id,
                quantity=data.quantity,
                reference_type="waste_record",
                reason=data.reason,
                notes=data.notes,
            ),
            movement_type=MovementType.waste,
        )

        unit_cost = await self.kardex_repo.get_last_unit_cost(
            data.ingredient_id, data.location_id
        )

        record = await self.repo.create(
            ingredient_id=data.ingredient_id,
            location_id=data.location_id,
            waste_category_id=data.waste_category_id,
            movement_id=movement.entity_id,
            quantity=data.quantity,
            unit_cost=unit_cost,
            waste_date=data.waste_date,
            reason=data.reason,
            notes=data.notes,
        )
        await self.session.commit()
        return record

    async def get_summary(
        self,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        location_id: UUID | None = None,
        waste_category_id: UUID | None = None,
    ) -> list[WasteSummaryLineOutput]:
        """
        Aggregates waste records by category, returning total quantity, total cost,
        and record count per category within the optional date/location/category filters.
        """
        from sqlalchemy import func
        from app.modules.waste.domain.models import WasteCategory as WCat

        filters = [WasteRecord.is_deleted.is_(False)]
        if from_date is not None:
            filters.append(WasteRecord.waste_date >= from_date)
        if to_date is not None:
            filters.append(WasteRecord.waste_date <= to_date)
        if location_id is not None:
            filters.append(WasteRecord.location_id == location_id)
        if waste_category_id is not None:
            filters.append(WasteRecord.waste_category_id == waste_category_id)

        stmt = (
            select(
                WasteRecord.waste_category_id,
                WCat.name.label("category_name"),
                func.sum(WasteRecord.quantity).label("total_quantity"),
                func.sum(WasteRecord.quantity * WasteRecord.unit_cost).label("total_cost"),
                func.count(WasteRecord.entity_id).label("record_count"),
            )
            .join(WCat, WasteRecord.waste_category_id == WCat.entity_id)
            .where(*filters)
            .group_by(WasteRecord.waste_category_id, WCat.name)
            .order_by(WCat.name)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            WasteSummaryLineOutput(
                waste_category_id=row.waste_category_id,
                category_name=row.category_name,
                total_quantity=row.total_quantity or Decimal("0"),
                total_cost=row.total_cost or Decimal("0"),
                record_count=row.record_count,
            )
            for row in rows
        ]
