from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.core.shared.infrastructure.repository import BaseRepository
from app.modules.purchasing.domain.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseInvoice,
    PurchaseOrder,
    PurchaseOrderLine,
)


class PurchaseOrderRepository(BaseRepository[PurchaseOrder]):
    model = PurchaseOrder

    async def get_by_number(self, po_number: str) -> PurchaseOrder | None:
        result = await self.session.execute(
            select(PurchaseOrder).where(
                PurchaseOrder.po_number == po_number,
                PurchaseOrder.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()


class PurchaseOrderLineRepository(BaseRepository[PurchaseOrderLine]):
    model = PurchaseOrderLine

    async def list_by_order(self, order_id: UUID) -> list[PurchaseOrderLine]:
        result = await self.session.execute(
            select(PurchaseOrderLine).where(
                PurchaseOrderLine.order_id == order_id,
                PurchaseOrderLine.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())

    async def get_by_order_and_ingredient(
        self, order_id: UUID, ingredient_id: UUID
    ) -> PurchaseOrderLine | None:
        result = await self.session.execute(
            select(PurchaseOrderLine).where(
                PurchaseOrderLine.order_id == order_id,
                PurchaseOrderLine.ingredient_id == ingredient_id,
                PurchaseOrderLine.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()


class GoodsReceiptRepository(BaseRepository[GoodsReceipt]):
    model = GoodsReceipt

    async def get_by_number(self, receipt_number: str) -> GoodsReceipt | None:
        result = await self.session.execute(
            select(GoodsReceipt).where(
                GoodsReceipt.receipt_number == receipt_number,
                GoodsReceipt.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_order(self, order_id: UUID) -> list[GoodsReceipt]:
        result = await self.session.execute(
            select(GoodsReceipt).where(
                GoodsReceipt.order_id == order_id,
                GoodsReceipt.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())


class GoodsReceiptLineRepository(BaseRepository[GoodsReceiptLine]):
    model = GoodsReceiptLine

    async def list_by_receipt(self, receipt_id: UUID) -> list[GoodsReceiptLine]:
        result = await self.session.execute(
            select(GoodsReceiptLine).where(
                GoodsReceiptLine.receipt_id == receipt_id,
                GoodsReceiptLine.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())

    async def get_by_receipt_and_ingredient(
        self, receipt_id: UUID, ingredient_id: UUID
    ) -> GoodsReceiptLine | None:
        result = await self.session.execute(
            select(GoodsReceiptLine).where(
                GoodsReceiptLine.receipt_id == receipt_id,
                GoodsReceiptLine.ingredient_id == ingredient_id,
                GoodsReceiptLine.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()


class PurchaseInvoiceRepository(BaseRepository[PurchaseInvoice]):
    model = PurchaseInvoice

    async def get_by_number(self, invoice_number: str) -> PurchaseInvoice | None:
        result = await self.session.execute(
            select(PurchaseInvoice).where(
                PurchaseInvoice.invoice_number == invoice_number,
                PurchaseInvoice.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_order(self, order_id: UUID) -> list[PurchaseInvoice]:
        result = await self.session.execute(
            select(PurchaseInvoice).where(
                PurchaseInvoice.order_id == order_id,
                PurchaseInvoice.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())
