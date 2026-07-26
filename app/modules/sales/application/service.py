from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.domain.exceptions import ConflictException, NotFoundException
from app.modules.catalog.infrastructure.repository import IngredientRepository
from app.modules.inventory.application.schemas import MovementExitInput
from app.modules.inventory.application.service import MovementService
from app.modules.inventory.domain.enums import MovementType
from app.modules.inventory.infrastructure.repository import (
    LocationRepository,
    StockItemRepository,
)
from app.modules.sales.application.schemas import (
    SalesOrderCreateInput,
    SalesOrderLineCreateInput,
    SalesOrderLineUpdateInput,
    SalesOrderUpdateInput,
)
from app.modules.sales.domain.enums import SalesOrderStatus
from app.modules.sales.domain.exceptions import (
    EmptySalesOrderException,
    InsufficientStockForSaleException,
    OrderAlreadyCancelledException,
    OrderAlreadyDeliveredException,
    OrderNotConfirmedException,
    OrderNotInPreparationException,
    OrderNotPendingException,
    OrderNotReadyException,
)
from app.modules.sales.domain.models import SalesOrder, SalesOrderLine
from app.modules.sales.infrastructure.filters import SalesOrderFilterSet
from app.modules.sales.infrastructure.repository import (
    SalesOrderLineRepository,
    SalesOrderRepository,
)


def _generate_order_number() -> str:
    today = date.today()
    suffix = uuid.uuid4().hex[:6].upper()
    return f"SO-{today.strftime('%Y%m')}-{suffix}"


async def _recalculate_total(
    session: AsyncSession,
    order: SalesOrder,
    line_repo: SalesOrderLineRepository,
) -> SalesOrder:
    lines = await line_repo.list_by_order(order.entity_id)
    total = sum(line.quantity * line.unit_price for line in lines)
    repo = SalesOrderRepository(session)
    return await repo.update(order, total_amount=total)


class SalesOrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SalesOrderRepository(session)
        self.line_repo = SalesOrderLineRepository(session)
        self.location_repo = LocationRepository(session)
        self.ingredient_repo = IngredientRepository(session)
        self.stock_repo = StockItemRepository(session)
        self.movement_svc = MovementService(session)

    async def get(self, order_id: UUID) -> SalesOrder:
        return await self.repo.get_or_404(order_id)

    async def list(self, params: dict) -> tuple[Sequence[SalesOrder], int]:
        return await self.repo.list(SalesOrderFilterSet, params)

    async def create(self, data: SalesOrderCreateInput) -> SalesOrder:
        await self.location_repo.get_or_404(data.source_location_id)
        order_number = _generate_order_number()
        if await self.repo.get_by_number(order_number) is not None:
            order_number = _generate_order_number()
        order = await self.repo.create(
            order_number=order_number,
            source_location_id=data.source_location_id,
            channel=data.channel,
            status=SalesOrderStatus.pending,
            table_reference=data.table_reference,
            notes=data.notes,
            total_amount=Decimal("0"),
        )
        await self.session.commit()
        return order

    async def update(self, order_id: UUID, data: SalesOrderUpdateInput) -> SalesOrder:
        order = await self.repo.get_or_404(order_id)
        if order.status not in (SalesOrderStatus.pending, SalesOrderStatus.confirmed):
            raise OrderNotPendingException(
                "Only pending or confirmed orders can be updated"
            )
        values = data.model_dump(exclude_none=True)
        order = await self.repo.update(order, **values)
        await self.session.commit()
        return order

    async def confirm(self, order_id: UUID) -> SalesOrder:
        """pending → confirmed. Validates lines exist and stock is available."""
        order = await self.repo.get_or_404(order_id)
        if order.status != SalesOrderStatus.pending:
            raise OrderNotPendingException("Only pending orders can be confirmed")
        lines = await self.line_repo.list_by_order(order_id)
        if not lines:
            raise EmptySalesOrderException("Cannot confirm an order with no lines")
        shortages: list[str] = []
        for line in lines:
            stock = await self.stock_repo.get_by_ingredient_and_location(
                line.ingredient_id, order.source_location_id
            )
            available = stock.quantity_available if stock is not None else Decimal("0")
            if available < line.quantity:
                shortages.append(
                    f"ingredient {line.ingredient_id}: "
                    f"required={line.quantity}, available={available}"
                )
        if shortages:
            raise InsufficientStockForSaleException(
                "Insufficient stock: " + "; ".join(shortages)
            )
        order = await self.repo.update(order, status=SalesOrderStatus.confirmed)
        await self.session.commit()
        return order

    async def start_preparation(self, order_id: UUID) -> SalesOrder:
        """confirmed → in_preparation."""
        order = await self.repo.get_or_404(order_id)
        if order.status != SalesOrderStatus.confirmed:
            raise OrderNotConfirmedException(
                "Only confirmed orders can be moved to preparation"
            )
        order = await self.repo.update(order, status=SalesOrderStatus.in_preparation)
        await self.session.commit()
        return order

    async def mark_ready(self, order_id: UUID) -> SalesOrder:
        """in_preparation → ready."""
        order = await self.repo.get_or_404(order_id)
        if order.status != SalesOrderStatus.in_preparation:
            raise OrderNotInPreparationException(
                "Only in-preparation orders can be marked ready"
            )
        order = await self.repo.update(order, status=SalesOrderStatus.ready)
        await self.session.commit()
        return order

    async def deliver(self, order_id: UUID) -> SalesOrder:
        """
        ready → delivered.

        Fires one sales_deduction exit movement per line from the source location.
        All movements are committed in a single transaction at the end.
        """
        order = await self.repo.get_or_404(order_id)
        if order.status == SalesOrderStatus.delivered:
            raise OrderAlreadyDeliveredException("Order is already delivered")
        if order.status != SalesOrderStatus.ready:
            raise OrderNotReadyException("Only ready orders can be delivered")
        lines = await self.line_repo.list_by_order(order_id)
        if not lines:
            raise EmptySalesOrderException("Cannot deliver an order with no lines")
        for line in lines:
            await self.movement_svc.record_exit(
                MovementExitInput(
                    ingredient_id=line.ingredient_id,
                    location_id=order.source_location_id,
                    quantity=line.quantity,
                    reference_type="sales_order",
                    reference_id=order.entity_id,
                    notes=f"Sales order {order.order_number}",
                ),
                movement_type=MovementType.sales_deduction,
            )
        order = await self.repo.update(order, status=SalesOrderStatus.delivered)
        await self.session.commit()
        return order

    async def cancel(self, order_id: UUID) -> SalesOrder:
        order = await self.repo.get_or_404(order_id)
        if order.status == SalesOrderStatus.cancelled:
            raise OrderAlreadyCancelledException("Order is already cancelled")
        if order.status == SalesOrderStatus.delivered:
            raise OrderAlreadyDeliveredException(
                "Delivered orders cannot be cancelled"
            )
        order = await self.repo.update(order, status=SalesOrderStatus.cancelled)
        await self.session.commit()
        return order

    # ---------- Lines ----------

    async def list_lines(self, order_id: UUID) -> list[SalesOrderLine]:
        await self.repo.get_or_404(order_id)
        return await self.line_repo.list_by_order(order_id)

    async def add_line(
        self, order_id: UUID, data: SalesOrderLineCreateInput
    ) -> SalesOrderLine:
        order = await self.repo.get_or_404(order_id)
        if order.status not in (SalesOrderStatus.pending, SalesOrderStatus.confirmed):
            raise OrderNotPendingException(
                "Lines can only be added to pending or confirmed orders"
            )
        ingredient = await self.ingredient_repo.get_or_404(data.ingredient_id)
        if not ingredient.is_active:
            raise ConflictException(
                f"Ingredient '{ingredient.name}' is not active"
            )
        existing = await self.line_repo.get_by_order_and_ingredient(
            order_id, data.ingredient_id
        )
        if existing is not None:
            raise ConflictException(
                "This ingredient already has a line on this order"
            )
        line = await self.line_repo.create(
            order_id=order_id,
            ingredient_id=data.ingredient_id,
            quantity=data.quantity,
            unit_price=data.unit_price,
        )
        # Reset to pending if it was confirmed (lines changed)
        if order.status == SalesOrderStatus.confirmed:
            await self.repo.update(order, status=SalesOrderStatus.pending)
        await _recalculate_total(self.session, order, self.line_repo)
        await self.session.commit()
        return line

    async def update_line(
        self,
        order_id: UUID,
        line_id: UUID,
        data: SalesOrderLineUpdateInput,
    ) -> SalesOrderLine:
        order = await self.repo.get_or_404(order_id)
        if order.status not in (SalesOrderStatus.pending, SalesOrderStatus.confirmed):
            raise OrderNotPendingException(
                "Lines can only be updated on pending or confirmed orders"
            )
        line = await self.line_repo.get_or_404(line_id)
        if line.order_id != order_id:
            raise NotFoundException("Order line not found on this order")
        values = data.model_dump(exclude_none=True)
        line = await self.line_repo.update(line, **values)
        if order.status == SalesOrderStatus.confirmed:
            await self.repo.update(order, status=SalesOrderStatus.pending)
        await _recalculate_total(self.session, order, self.line_repo)
        await self.session.commit()
        return line

    async def remove_line(self, order_id: UUID, line_id: UUID) -> None:
        order = await self.repo.get_or_404(order_id)
        if order.status not in (SalesOrderStatus.pending, SalesOrderStatus.confirmed):
            raise OrderNotPendingException(
                "Lines can only be removed from pending or confirmed orders"
            )
        line = await self.line_repo.get_or_404(line_id)
        if line.order_id != order_id:
            raise NotFoundException("Order line not found on this order")
        await self.line_repo.soft_delete(line)
        if order.status == SalesOrderStatus.confirmed:
            await self.repo.update(order, status=SalesOrderStatus.pending)
        await _recalculate_total(self.session, order, self.line_repo)
        await self.session.commit()
