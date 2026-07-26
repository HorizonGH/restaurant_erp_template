from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.core.shared.infrastructure.repository import BaseRepository
from app.modules.sales.domain.models import SalesOrder, SalesOrderLine


class SalesOrderRepository(BaseRepository[SalesOrder]):
    model = SalesOrder

    async def get_by_number(self, order_number: str) -> SalesOrder | None:
        result = await self.session.execute(
            select(SalesOrder).where(
                SalesOrder.order_number == order_number,
                SalesOrder.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()


class SalesOrderLineRepository(BaseRepository[SalesOrderLine]):
    model = SalesOrderLine

    async def list_by_order(self, order_id: UUID) -> list[SalesOrderLine]:
        result = await self.session.execute(
            select(SalesOrderLine).where(
                SalesOrderLine.order_id == order_id,
                SalesOrderLine.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())

    async def get_by_order_and_ingredient(
        self, order_id: UUID, ingredient_id: UUID
    ) -> SalesOrderLine | None:
        result = await self.session.execute(
            select(SalesOrderLine).where(
                SalesOrderLine.order_id == order_id,
                SalesOrderLine.ingredient_id == ingredient_id,
                SalesOrderLine.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()
