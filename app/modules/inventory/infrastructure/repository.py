from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from app.core.shared.infrastructure.repository import BaseRepository
from app.modules.catalog.domain.models import Ingredient
from app.modules.inventory.domain.models import (
    Batch,
    KardexEntry,
    Location,
    StockItem,
    StockMovement,
)


class LocationRepository(BaseRepository[Location]):
    model = Location

    async def list_active(self) -> list[Location]:
        result = await self.session.execute(
            select(Location)
            .where(Location.is_deleted.is_(False), Location.is_active.is_(True))
            .order_by(Location.name)
        )
        return list(result.scalars().all())

    async def get_by_code(self, code: str) -> Location | None:
        result = await self.session.execute(
            select(Location).where(Location.code == code, Location.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    async def has_stock_items(self, location_id: UUID) -> bool:
        result = await self.session.execute(
            select(func.count()).where(
                StockItem.location_id == location_id,
                StockItem.is_deleted.is_(False),
            )
        )
        return result.scalar_one() > 0


class StockItemRepository(BaseRepository[StockItem]):
    model = StockItem

    async def get_by_ingredient_and_location(
        self, ingredient_id: UUID, location_id: UUID
    ) -> StockItem | None:
        result = await self.session.execute(
            select(StockItem).where(
                StockItem.ingredient_id == ingredient_id,
                StockItem.location_id == location_id,
                StockItem.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_low_stock(self) -> list[StockItem]:
        result = await self.session.execute(
            select(StockItem)
            .join(Ingredient, StockItem.ingredient_id == Ingredient.entity_id)
            .where(
                StockItem.quantity_on_hand <= Ingredient.reorder_point,
                StockItem.is_deleted.is_(False),
                Ingredient.is_deleted.is_(False),
                Ingredient.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def list_by_location(self, location_id: UUID) -> list[StockItem]:
        result = await self.session.execute(
            select(StockItem).where(
                StockItem.location_id == location_id,
                StockItem.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())

    async def list_by_ingredient(self, ingredient_id: UUID) -> list[StockItem]:
        result = await self.session.execute(
            select(StockItem).where(
                StockItem.ingredient_id == ingredient_id,
                StockItem.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())


class BatchRepository(BaseRepository[Batch]):
    model = Batch

    async def list_for_exit(self, ingredient_id: UUID, location_id: UUID) -> list[Batch]:
        result = await self.session.execute(
            select(Batch)
            .where(
                Batch.ingredient_id == ingredient_id,
                Batch.location_id == location_id,
                Batch.quantity > 0,
                Batch.is_deleted.is_(False),
            )
            .order_by(Batch.received_date.asc(), Batch.expiry_date.asc().nulls_last())
        )
        return list(result.scalars().all())

    async def list_expiring_before(self, target_date: date) -> list[Batch]:
        result = await self.session.execute(
            select(Batch).where(
                Batch.expiry_date <= target_date,
                Batch.quantity > 0,
                Batch.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())


class StockMovementRepository(BaseRepository[StockMovement]):
    model = StockMovement


class KardexRepository(BaseRepository[KardexEntry]):
    model = KardexEntry

    async def get_last_balance(self, ingredient_id: UUID, location_id: UUID) -> Decimal:
        result = await self.session.execute(
            select(KardexEntry.quantity_balance)
            .where(
                KardexEntry.ingredient_id == ingredient_id,
                KardexEntry.location_id == location_id,
            )
            .order_by(KardexEntry.movement_date.desc(), KardexEntry.created_at.desc())
            .limit(1)
        )
        value = result.scalar_one_or_none()
        return value if value is not None else Decimal("0")

    async def get_last_unit_cost(self, ingredient_id: UUID, location_id: UUID) -> Decimal:
        result = await self.session.execute(
            select(KardexEntry.unit_cost)
            .where(
                KardexEntry.ingredient_id == ingredient_id,
                KardexEntry.location_id == location_id,
            )
            .order_by(KardexEntry.movement_date.desc(), KardexEntry.created_at.desc())
            .limit(1)
        )
        value = result.scalar_one_or_none()
        return value if value is not None else Decimal("0")
