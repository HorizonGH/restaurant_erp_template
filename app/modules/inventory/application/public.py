from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.domain.exceptions import NotFoundException
from app.modules.inventory.application.schemas import MovementExitInput
from app.modules.inventory.application.service import MovementService
from app.modules.inventory.domain.enums import MovementType
from app.modules.inventory.domain.exceptions import InsufficientStockException
from app.modules.inventory.infrastructure.repository import StockItemRepository


class InventoryPublicService:
    """Only this class may be imported by other modules (purchasing, production, sales, waste)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.stock_repo = StockItemRepository(session)
        self.movement_service = MovementService(session)

    async def get_stock_level(self, ingredient_id: UUID, location_id: UUID) -> Decimal:
        item = await self.stock_repo.get_by_ingredient_and_location(ingredient_id, location_id)
        if item is None:
            return Decimal("0")
        return item.quantity_available

    async def reserve_stock(
        self,
        ingredient_id: UUID,
        location_id: UUID,
        quantity: Decimal,
        reference_id: UUID,
    ) -> None:
        item = await self.stock_repo.get_by_ingredient_and_location(ingredient_id, location_id)
        if item is None:
            raise NotFoundException("No stock found for this ingredient at this location")
        if item.quantity_available < quantity:
            raise InsufficientStockException(
                f"Cannot reserve {quantity}: only {item.quantity_available} available"
            )
        await self.stock_repo.update(
            item, quantity_reserved=item.quantity_reserved + quantity
        )
        await self.session.commit()

    async def release_reservation(
        self,
        ingredient_id: UUID,
        location_id: UUID,
        quantity: Decimal,
    ) -> None:
        item = await self.stock_repo.get_by_ingredient_and_location(ingredient_id, location_id)
        if item is None:
            return
        new_reserved = max(Decimal("0"), item.quantity_reserved - quantity)
        await self.stock_repo.update(item, quantity_reserved=new_reserved)
        await self.session.commit()

    async def deduct_stock(
        self,
        ingredient_id: UUID,
        location_id: UUID,
        quantity: Decimal,
        movement_type: MovementType,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
    ) -> UUID:
        data = MovementExitInput(
            ingredient_id=ingredient_id,
            location_id=location_id,
            quantity=quantity,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        movement = await self.movement_service.record_exit(data, movement_type=movement_type)
        return movement.entity_id
