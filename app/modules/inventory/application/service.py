from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.domain.exceptions import ConflictException, NotFoundException
from app.core.shared.domain.helpers import utcnow
from app.modules.catalog.infrastructure.repository import IngredientRepository
from app.modules.inventory.application.schemas import (
    BatchCreateInput,
    BatchUpdateInput,
    LocationCreateInput,
    LocationUpdateInput,
    MovementAdjustmentInput,
    MovementEntryInput,
    MovementExitInput,
)
from app.modules.inventory.domain.enums import MovementType
from app.modules.inventory.domain.exceptions import (
    InsufficientStockException,
    LocationInUseException,
)
from app.modules.inventory.domain.models import (
    Batch,
    KardexEntry,
    Location,
    StockItem,
    StockMovement,
)
from app.modules.inventory.infrastructure.filters import (
    BatchFilterSet,
    KardexFilterSet,
    LocationFilterSet,
    StockItemFilterSet,
    StockMovementFilterSet,
)
from app.modules.inventory.infrastructure.repository import (
    BatchRepository,
    KardexRepository,
    LocationRepository,
    StockItemRepository,
    StockMovementRepository,
)


class LocationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = LocationRepository(session)

    async def get(self, location_id: UUID) -> Location:
        return await self.repo.get_or_404(location_id)

    async def select(self) -> list[Location]:
        return await self.repo.list_active()

    async def list(self, params: dict) -> tuple[Sequence[Location], int]:
        return await self.repo.list(LocationFilterSet, params)

    async def create(self, data: LocationCreateInput) -> Location:
        existing = await self.repo.get_by_code(data.code)
        if existing is not None:
            raise ConflictException(f"Location with code '{data.code}' already exists")
        location = await self.repo.create(**data.model_dump())
        await self.session.commit()
        return location

    async def update(self, location_id: UUID, data: LocationUpdateInput) -> Location:
        location = await self.repo.get_or_404(location_id)
        values = data.model_dump(exclude_none=True)
        if "code" in values:
            existing = await self.repo.get_by_code(values["code"])
            if existing is not None and existing.entity_id != location_id:
                raise ConflictException(
                    f"Location with code '{values['code']}' already exists"
                )
        location = await self.repo.update(location, **values)
        await self.session.commit()
        return location

    async def delete(self, location_id: UUID) -> None:
        location = await self.repo.get_or_404(location_id)
        if await self.repo.has_stock_items(location_id):
            raise LocationInUseException("Cannot delete location with stock items")
        await self.repo.soft_delete(location)
        await self.session.commit()

    async def set_active(self, location_id: UUID, *, is_active: bool) -> Location:
        location = await self.repo.get_or_404(location_id)
        location = await self.repo.update(location, is_active=is_active)
        await self.session.commit()
        return location


class MovementService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ingredient_repo = IngredientRepository(session)
        self.location_repo = LocationRepository(session)
        self.stock_repo = StockItemRepository(session)
        self.batch_repo = BatchRepository(session)
        self.movement_repo = StockMovementRepository(session)
        self.kardex_repo = KardexRepository(session)

    async def record_entry(self, data: MovementEntryInput) -> StockMovement:
        await self.ingredient_repo.get_or_404(data.ingredient_id)
        await self.location_repo.get_or_404(data.location_id)

        batch = await self.batch_repo.create(
            ingredient_id=data.ingredient_id,
            location_id=data.location_id,
            batch_number=data.batch_number,
            lot_number=data.lot_number,
            quantity=data.quantity,
            expiry_date=data.expiry_date,
            received_date=data.received_date,
            unit_cost=data.unit_cost,
            supplier_id=data.supplier_id,
        )

        stock_item = await self.stock_repo.get_by_ingredient_and_location(
            data.ingredient_id, data.location_id
        )
        if stock_item is None:
            stock_item = await self.stock_repo.create(
                ingredient_id=data.ingredient_id,
                location_id=data.location_id,
                quantity_on_hand=data.quantity,
                quantity_reserved=Decimal("0"),
            )
        else:
            await self.stock_repo.update(
                stock_item,
                quantity_on_hand=stock_item.quantity_on_hand + data.quantity,
            )

        movement = await self.movement_repo.create(
            ingredient_id=data.ingredient_id,
            location_id=data.location_id,
            batch_id=batch.entity_id,
            movement_type=MovementType.entry,
            quantity=data.quantity,
            unit_cost=data.unit_cost,
            reference_type=data.reference_type,
            reference_id=data.reference_id,
            notes=data.notes,
        )

        previous_balance = await self.kardex_repo.get_last_balance(
            data.ingredient_id, data.location_id
        )
        new_balance = previous_balance + data.quantity
        value_change = data.quantity * data.unit_cost

        await self.kardex_repo.create(
            ingredient_id=data.ingredient_id,
            location_id=data.location_id,
            movement_id=movement.entity_id,
            movement_date=utcnow(),
            movement_type=MovementType.entry,
            quantity_in=data.quantity,
            quantity_out=Decimal("0"),
            quantity_balance=new_balance,
            unit_cost=data.unit_cost,
            total_value_change=value_change,
            balance_value=new_balance * data.unit_cost,
        )

        await self.session.commit()
        return movement

    async def record_exit(
        self,
        data: MovementExitInput,
        movement_type: MovementType = MovementType.exit,
    ) -> StockMovement:
        stock_item = await self.stock_repo.get_by_ingredient_and_location(
            data.ingredient_id, data.location_id
        )
        if stock_item is None:
            raise NotFoundException("No stock found for this ingredient at this location")
        if stock_item.quantity_available < data.quantity:
            raise InsufficientStockException(
                f"Insufficient stock: available={stock_item.quantity_available}, "
                f"requested={data.quantity}"
            )

        batches = await self.batch_repo.list_for_exit(data.ingredient_id, data.location_id)
        remaining = data.quantity
        first_batch_id: UUID | None = None
        for batch in batches:
            if remaining <= Decimal("0"):
                break
            consumed = min(batch.quantity, remaining)
            await self.batch_repo.update(batch, quantity=batch.quantity - consumed)
            remaining -= consumed
            if first_batch_id is None:
                first_batch_id = batch.entity_id

        unit_cost = await self.kardex_repo.get_last_unit_cost(
            data.ingredient_id, data.location_id
        )

        await self.stock_repo.update(
            stock_item,
            quantity_on_hand=stock_item.quantity_on_hand - data.quantity,
        )

        movement = await self.movement_repo.create(
            ingredient_id=data.ingredient_id,
            location_id=data.location_id,
            batch_id=first_batch_id,
            movement_type=movement_type,
            quantity=data.quantity,
            unit_cost=unit_cost,
            reference_type=data.reference_type,
            reference_id=data.reference_id,
            reason=data.reason,
            notes=data.notes,
        )

        previous_balance = await self.kardex_repo.get_last_balance(
            data.ingredient_id, data.location_id
        )
        new_balance = previous_balance - data.quantity
        value_change = -(data.quantity * unit_cost)

        await self.kardex_repo.create(
            ingredient_id=data.ingredient_id,
            location_id=data.location_id,
            movement_id=movement.entity_id,
            movement_date=utcnow(),
            movement_type=movement_type,
            quantity_in=Decimal("0"),
            quantity_out=data.quantity,
            quantity_balance=new_balance,
            unit_cost=unit_cost,
            total_value_change=value_change,
            balance_value=new_balance * unit_cost,
        )

        await self.session.commit()
        return movement

    async def record_adjustment(self, data: MovementAdjustmentInput) -> StockMovement:
        await self.ingredient_repo.get_or_404(data.ingredient_id)
        await self.location_repo.get_or_404(data.location_id)

        stock_item = await self.stock_repo.get_by_ingredient_and_location(
            data.ingredient_id, data.location_id
        )
        new_quantity = (
            stock_item.quantity_on_hand + data.quantity_delta
            if stock_item is not None
            else data.quantity_delta
        )
        if new_quantity < Decimal("0"):
            raise InsufficientStockException(
                "Adjustment would result in negative stock"
            )

        unit_cost = data.unit_cost or await self.kardex_repo.get_last_unit_cost(
            data.ingredient_id, data.location_id
        )

        if stock_item is None:
            stock_item = await self.stock_repo.create(
                ingredient_id=data.ingredient_id,
                location_id=data.location_id,
                quantity_on_hand=new_quantity,
                quantity_reserved=Decimal("0"),
            )
        else:
            await self.stock_repo.update(stock_item, quantity_on_hand=new_quantity)

        abs_quantity = abs(data.quantity_delta)
        movement = await self.movement_repo.create(
            ingredient_id=data.ingredient_id,
            location_id=data.location_id,
            batch_id=None,
            movement_type=MovementType.adjustment,
            quantity=abs_quantity,
            unit_cost=unit_cost,
            reason=data.reason,
            notes=data.notes,
        )

        previous_balance = await self.kardex_repo.get_last_balance(
            data.ingredient_id, data.location_id
        )
        qty_in = data.quantity_delta if data.quantity_delta > 0 else Decimal("0")
        qty_out = abs(data.quantity_delta) if data.quantity_delta < 0 else Decimal("0")
        new_balance = previous_balance + data.quantity_delta
        value_change = data.quantity_delta * unit_cost

        await self.kardex_repo.create(
            ingredient_id=data.ingredient_id,
            location_id=data.location_id,
            movement_id=movement.entity_id,
            movement_date=utcnow(),
            movement_type=MovementType.adjustment,
            quantity_in=qty_in,
            quantity_out=qty_out,
            quantity_balance=new_balance,
            unit_cost=unit_cost,
            total_value_change=value_change,
            balance_value=new_balance * unit_cost,
        )

        await self.session.commit()
        return movement


class StockService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = StockItemRepository(session)

    async def list_stock(self, params: dict) -> tuple[Sequence[StockItem], int]:
        return await self.repo.list(StockItemFilterSet, params)

    async def list_low_stock(self) -> list[StockItem]:
        return await self.repo.list_low_stock()

    async def get_by_ingredient_location(
        self, ingredient_id: UUID, location_id: UUID
    ) -> StockItem:
        item = await self.repo.get_by_ingredient_and_location(ingredient_id, location_id)
        if item is None:
            raise NotFoundException("No stock found for this ingredient at this location")
        return item

    async def list_by_ingredient(self, ingredient_id: UUID) -> list[StockItem]:
        return await self.repo.list_by_ingredient(ingredient_id)


class BatchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = BatchRepository(session)

    async def get(self, batch_id: UUID) -> Batch:
        return await self.repo.get_or_404(batch_id)

    async def list(self, params: dict) -> tuple[Sequence[Batch], int]:
        return await self.repo.list(BatchFilterSet, params)

    async def list_expiring_soon(self, days: int = 7) -> list[Batch]:
        from datetime import date

        target = date.today() + timedelta(days=days)
        return await self.repo.list_expiring_before(target)


class KardexService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = KardexRepository(session)

    async def list_kardex(self, params: dict) -> tuple[Sequence[KardexEntry], int]:
        return await self.repo.list(KardexFilterSet, params)
