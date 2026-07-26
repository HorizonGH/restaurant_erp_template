from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.domain.exceptions import ConflictException, NotFoundException
from app.modules.catalog.infrastructure.repository import IngredientRepository, SupplierRepository
from app.modules.inventory.application.schemas import MovementEntryInput
from app.modules.inventory.application.service import MovementService
from app.modules.inventory.infrastructure.repository import LocationRepository
from app.modules.purchasing.application.schemas import (
    InvoiceCreateInput,
    InvoiceUpdateInput,
    POCreateInput,
    POLineCreateInput,
    POLineUpdateInput,
    POUpdateInput,
    ReceiptCreateInput,
    ReceiptLineCreateInput,
    ReceiptLineUpdateInput,
    ReceiptUpdateInput,
)
from app.modules.purchasing.domain.enums import InvoiceStatus, POStatus, ReceiptStatus
from app.modules.purchasing.domain.exceptions import (
    EmptyPOException,
    EmptyReceiptException,
    InvoiceAlreadyMatchedException,
    POAlreadyCancelledException,
    POAlreadyReceivedException,
    PONotDraftException,
    PONotSentException,
    ReceiptAlreadyCompletedException,
    ReceiptNotDraftException,
)
from app.modules.purchasing.domain.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseInvoice,
    PurchaseOrder,
    PurchaseOrderLine,
)
from app.modules.purchasing.infrastructure.filters import (
    GoodsReceiptFilterSet,
    GoodsReceiptLineFilterSet,
    PurchaseInvoiceFilterSet,
    PurchaseOrderFilterSet,
    PurchaseOrderLineFilterSet,
)
from app.modules.purchasing.infrastructure.repository import (
    GoodsReceiptLineRepository,
    GoodsReceiptRepository,
    PurchaseInvoiceRepository,
    PurchaseOrderLineRepository,
    PurchaseOrderRepository,
)


def _generate_po_number() -> str:
    today = date.today()
    suffix = uuid.uuid4().hex[:5].upper()
    return f"PO-{today.strftime('%Y%m')}-{suffix}"


def _generate_receipt_number() -> str:
    today = date.today()
    suffix = uuid.uuid4().hex[:5].upper()
    return f"GR-{today.strftime('%Y%m')}-{suffix}"


async def _recalculate_total(
    session: AsyncSession,
    order: PurchaseOrder,
    line_repo: PurchaseOrderLineRepository,
) -> PurchaseOrder:
    lines = await line_repo.list_by_order(order.entity_id)
    total = sum(line.ordered_quantity * line.unit_cost for line in lines)
    po_repo = PurchaseOrderRepository(session)
    return await po_repo.update(order, total_amount=total)


async def _update_po_status(
    session: AsyncSession,
    order: PurchaseOrder,
    line_repo: PurchaseOrderLineRepository,
) -> PurchaseOrder:
    """Recalculate PO status after a receipt completes."""
    lines = await line_repo.list_by_order(order.entity_id)
    if not lines:
        return order
    all_received = all(line.is_fully_received for line in lines)
    any_received = any(line.received_quantity > 0 for line in lines)
    po_repo = PurchaseOrderRepository(session)
    if all_received:
        return await po_repo.update(order, status=POStatus.received)
    if any_received:
        return await po_repo.update(order, status=POStatus.partially_received)
    return order


# ---------------------------------------------------------------------------
# PurchaseOrderService
# ---------------------------------------------------------------------------

class PurchaseOrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PurchaseOrderRepository(session)
        self.line_repo = PurchaseOrderLineRepository(session)
        self.supplier_repo = SupplierRepository(session)
        self.ingredient_repo = IngredientRepository(session)

    async def get(self, order_id: UUID) -> PurchaseOrder:
        return await self.repo.get_or_404(order_id)

    async def list(self, params: dict) -> tuple[Sequence[PurchaseOrder], int]:
        return await self.repo.list(PurchaseOrderFilterSet, params)

    async def create(self, data: POCreateInput) -> PurchaseOrder:
        await self.supplier_repo.get_or_404(data.supplier_id)

        po_number = _generate_po_number()
        if await self.repo.get_by_number(po_number) is not None:
            po_number = _generate_po_number()

        order = await self.repo.create(
            po_number=po_number,
            supplier_id=data.supplier_id,
            status=POStatus.draft,
            expected_delivery_date=data.expected_delivery_date,
            notes=data.notes,
            total_amount=Decimal("0"),
        )
        await self.session.commit()
        return order

    async def update(self, order_id: UUID, data: POUpdateInput) -> PurchaseOrder:
        order = await self.repo.get_or_404(order_id)
        if order.status not in (POStatus.draft, POStatus.sent):
            raise PONotDraftException("Only draft or sent orders can be updated")
        values = data.model_dump(exclude_none=True)
        order = await self.repo.update(order, **values)
        await self.session.commit()
        return order

    async def send(self, order_id: UUID) -> PurchaseOrder:
        order = await self.repo.get_or_404(order_id)
        if order.status != POStatus.draft:
            raise PONotDraftException("Only draft orders can be sent")
        lines = await self.line_repo.list_by_order(order_id)
        if not lines:
            raise EmptyPOException("Cannot send a purchase order with no lines")
        order = await self.repo.update(order, status=POStatus.sent)
        await self.session.commit()
        return order

    async def cancel(self, order_id: UUID) -> PurchaseOrder:
        order = await self.repo.get_or_404(order_id)
        if order.status == POStatus.cancelled:
            raise POAlreadyCancelledException("Order is already cancelled")
        if order.status == POStatus.received:
            raise POAlreadyReceivedException("Fully received orders cannot be cancelled")
        order = await self.repo.update(order, status=POStatus.cancelled)
        await self.session.commit()
        return order

    async def add_line(self, order_id: UUID, data: POLineCreateInput) -> PurchaseOrderLine:
        order = await self.repo.get_or_404(order_id)
        if order.status != POStatus.draft:
            raise PONotDraftException("Lines can only be added to draft orders")
        await self.ingredient_repo.get_or_404(data.ingredient_id)
        existing = await self.line_repo.get_by_order_and_ingredient(order_id, data.ingredient_id)
        if existing is not None:
            raise ConflictException("This ingredient already has a line on this order")
        line = await self.line_repo.create(
            order_id=order_id,
            ingredient_id=data.ingredient_id,
            ordered_quantity=data.ordered_quantity,
            received_quantity=Decimal("0"),
            unit_cost=data.unit_cost,
        )
        await _recalculate_total(self.session, order, self.line_repo)
        await self.session.commit()
        return line

    async def update_line(
        self, order_id: UUID, line_id: UUID, data: POLineUpdateInput
    ) -> PurchaseOrderLine:
        order = await self.repo.get_or_404(order_id)
        if order.status != POStatus.draft:
            raise PONotDraftException("Lines can only be updated on draft orders")
        line = await self.line_repo.get_or_404(line_id)
        if line.order_id != order_id:
            raise NotFoundException("Order line not found on this order")
        values = data.model_dump(exclude_none=True)
        line = await self.line_repo.update(line, **values)
        await _recalculate_total(self.session, order, self.line_repo)
        await self.session.commit()
        return line

    async def remove_line(self, order_id: UUID, line_id: UUID) -> None:
        order = await self.repo.get_or_404(order_id)
        if order.status != POStatus.draft:
            raise PONotDraftException("Lines can only be removed from draft orders")
        line = await self.line_repo.get_or_404(line_id)
        if line.order_id != order_id:
            raise NotFoundException("Order line not found on this order")
        await self.line_repo.soft_delete(line)
        await _recalculate_total(self.session, order, self.line_repo)
        await self.session.commit()

    async def list_lines(self, order_id: UUID) -> list[PurchaseOrderLine]:
        await self.repo.get_or_404(order_id)
        return await self.line_repo.list_by_order(order_id)


# ---------------------------------------------------------------------------
# ReceivingService
# ---------------------------------------------------------------------------

class ReceivingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.receipt_repo = GoodsReceiptRepository(session)
        self.receipt_line_repo = GoodsReceiptLineRepository(session)
        self.order_repo = PurchaseOrderRepository(session)
        self.order_line_repo = PurchaseOrderLineRepository(session)
        self.location_repo = LocationRepository(session)
        self.ingredient_repo = IngredientRepository(session)
        self.movement_svc = MovementService(session)

    async def get(self, receipt_id: UUID) -> GoodsReceipt:
        return await self.receipt_repo.get_or_404(receipt_id)

    async def list(self, params: dict) -> tuple[Sequence[GoodsReceipt], int]:
        return await self.receipt_repo.list(GoodsReceiptFilterSet, params)

    async def create(self, data: ReceiptCreateInput) -> GoodsReceipt:
        order = await self.order_repo.get_or_404(data.order_id)
        if order.status not in (POStatus.sent, POStatus.partially_received):
            raise PONotSentException(
                "Receipts can only be created for sent or partially received orders"
            )
        await self.location_repo.get_or_404(data.destination_location_id)

        receipt_number = _generate_receipt_number()
        if await self.receipt_repo.get_by_number(receipt_number) is not None:
            receipt_number = _generate_receipt_number()

        receipt = await self.receipt_repo.create(
            receipt_number=receipt_number,
            order_id=data.order_id,
            destination_location_id=data.destination_location_id,
            status=ReceiptStatus.draft,
            notes=data.notes,
        )
        await self.session.commit()
        return receipt

    async def update(self, receipt_id: UUID, data: ReceiptUpdateInput) -> GoodsReceipt:
        receipt = await self.receipt_repo.get_or_404(receipt_id)
        if receipt.status != ReceiptStatus.draft:
            raise ReceiptNotDraftException("Only draft receipts can be updated")
        receipt = await self.receipt_repo.update(receipt, notes=data.notes)
        await self.session.commit()
        return receipt

    async def add_line(
        self, receipt_id: UUID, data: ReceiptLineCreateInput
    ) -> GoodsReceiptLine:
        receipt = await self.receipt_repo.get_or_404(receipt_id)
        if receipt.status != ReceiptStatus.draft:
            raise ReceiptNotDraftException("Lines can only be added to draft receipts")
        await self.ingredient_repo.get_or_404(data.ingredient_id)
        existing = await self.receipt_line_repo.get_by_receipt_and_ingredient(
            receipt_id, data.ingredient_id
        )
        if existing is not None:
            raise ConflictException("This ingredient already has a line on this receipt")
        line = await self.receipt_line_repo.create(
            receipt_id=receipt_id,
            ingredient_id=data.ingredient_id,
            batch_number=data.batch_number,
            lot_number=data.lot_number,
            expiry_date=data.expiry_date,
            received_quantity=data.received_quantity,
            unit_cost=data.unit_cost,
        )
        await self.session.commit()
        return line

    async def update_line(
        self, receipt_id: UUID, line_id: UUID, data: ReceiptLineUpdateInput
    ) -> GoodsReceiptLine:
        receipt = await self.receipt_repo.get_or_404(receipt_id)
        if receipt.status != ReceiptStatus.draft:
            raise ReceiptNotDraftException("Lines can only be updated on draft receipts")
        line = await self.receipt_line_repo.get_or_404(line_id)
        if line.receipt_id != receipt_id:
            raise NotFoundException("Receipt line not found on this receipt")
        values = data.model_dump(exclude_none=True)
        line = await self.receipt_line_repo.update(line, **values)
        await self.session.commit()
        return line

    async def remove_line(self, receipt_id: UUID, line_id: UUID) -> None:
        receipt = await self.receipt_repo.get_or_404(receipt_id)
        if receipt.status != ReceiptStatus.draft:
            raise ReceiptNotDraftException("Lines can only be removed from draft receipts")
        line = await self.receipt_line_repo.get_or_404(line_id)
        if line.receipt_id != receipt_id:
            raise NotFoundException("Receipt line not found on this receipt")
        await self.receipt_line_repo.soft_delete(line)
        await self.session.commit()

    async def complete(self, receipt_id: UUID) -> GoodsReceipt:
        """
        For each receipt line:
          1. Create an inventory entry movement (reference_type=goods_receipt)
          2. Update the PO line's received_quantity
          3. Recalculate PO status (partially_received / received)
        All inside a single logical transaction (MovementService commits per line,
        but the PO status update is committed here at the end).
        """
        receipt = await self.receipt_repo.get_or_404(receipt_id)
        if receipt.status == ReceiptStatus.completed:
            raise ReceiptAlreadyCompletedException("Receipt is already completed")
        if receipt.status != ReceiptStatus.draft:
            raise ReceiptNotDraftException("Only draft receipts can be completed")

        lines = await self.receipt_line_repo.list_by_receipt(receipt_id)
        if not lines:
            raise EmptyReceiptException("Cannot complete a receipt with no lines")

        order = await self.order_repo.get_or_404(receipt.order_id)

        for line in lines:
            # Record inventory entry
            await self.movement_svc.record_entry(
                MovementEntryInput(
                    ingredient_id=line.ingredient_id,
                    location_id=receipt.destination_location_id,
                    quantity=line.received_quantity,
                    unit_cost=line.unit_cost,
                    batch_number=line.batch_number,
                    lot_number=line.lot_number,
                    expiry_date=line.expiry_date,
                    received_date=date.today(),
                    reference_type="goods_receipt",
                    reference_id=receipt.entity_id,
                    notes=f"Receipt {receipt.receipt_number} — PO {order.po_number}",
                )
            )
            # Update received_quantity on the PO line
            po_line = await self.order_line_repo.get_by_order_and_ingredient(
                receipt.order_id, line.ingredient_id
            )
            if po_line is not None:
                new_received = po_line.received_quantity + line.received_quantity
                await self.order_line_repo.update(po_line, received_quantity=new_received)

        # Recalculate PO status
        await _update_po_status(self.session, order, self.order_line_repo)

        receipt = await self.receipt_repo.update(receipt, status=ReceiptStatus.completed)
        await self.session.commit()
        return receipt

    async def cancel(self, receipt_id: UUID) -> GoodsReceipt:
        receipt = await self.receipt_repo.get_or_404(receipt_id)
        if receipt.status == ReceiptStatus.completed:
            raise ReceiptAlreadyCompletedException("Completed receipts cannot be cancelled")
        receipt = await self.receipt_repo.update(receipt, status=ReceiptStatus.cancelled)
        await self.session.commit()
        return receipt

    async def list_lines(self, receipt_id: UUID) -> list[GoodsReceiptLine]:
        await self.receipt_repo.get_or_404(receipt_id)
        return await self.receipt_line_repo.list_by_receipt(receipt_id)

    async def list_by_order(self, order_id: UUID) -> list[GoodsReceipt]:
        await self.order_repo.get_or_404(order_id)
        return await self.receipt_repo.list_by_order(order_id)


# ---------------------------------------------------------------------------
# InvoiceService
# ---------------------------------------------------------------------------

class InvoiceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PurchaseInvoiceRepository(session)
        self.order_repo = PurchaseOrderRepository(session)

    async def get(self, invoice_id: UUID) -> PurchaseInvoice:
        return await self.repo.get_or_404(invoice_id)

    async def list(self, params: dict) -> tuple[Sequence[PurchaseInvoice], int]:
        return await self.repo.list(PurchaseInvoiceFilterSet, params)

    async def create(self, data: InvoiceCreateInput) -> PurchaseInvoice:
        order = await self.order_repo.get_or_404(data.order_id)
        if order.status == POStatus.draft:
            raise PONotSentException("Cannot invoice a draft purchase order")
        if order.status == POStatus.cancelled:
            raise POAlreadyCancelledException("Cannot invoice a cancelled purchase order")
        existing = await self.repo.get_by_number(data.invoice_number)
        if existing is not None:
            raise ConflictException(
                f"Invoice number '{data.invoice_number}' already exists"
            )
        invoice = await self.repo.create(
            invoice_number=data.invoice_number,
            order_id=data.order_id,
            status=InvoiceStatus.pending,
            invoice_date=data.invoice_date,
            due_date=data.due_date,
            total_amount=data.total_amount,
            notes=data.notes,
        )
        await self.session.commit()
        return invoice

    async def update(self, invoice_id: UUID, data: InvoiceUpdateInput) -> PurchaseInvoice:
        invoice = await self.repo.get_or_404(invoice_id)
        if invoice.status == InvoiceStatus.matched:
            raise InvoiceAlreadyMatchedException("Matched invoices cannot be updated")
        values = data.model_dump(exclude_none=True)
        invoice = await self.repo.update(invoice, **values)
        await self.session.commit()
        return invoice

    async def match(self, invoice_id: UUID) -> PurchaseInvoice:
        """Mark an invoice as matched to its PO — confirmed amounts are correct."""
        invoice = await self.repo.get_or_404(invoice_id)
        if invoice.status == InvoiceStatus.matched:
            raise InvoiceAlreadyMatchedException("Invoice is already matched")
        invoice = await self.repo.update(invoice, status=InvoiceStatus.matched)
        await self.session.commit()
        return invoice

    async def mark_paid(self, invoice_id: UUID) -> PurchaseInvoice:
        invoice = await self.repo.get_or_404(invoice_id)
        if invoice.status != InvoiceStatus.matched:
            raise InvoiceAlreadyMatchedException(
                "Only matched invoices can be marked as paid"
            )
        invoice = await self.repo.update(invoice, status=InvoiceStatus.paid)
        await self.session.commit()
        return invoice

    async def dispute(self, invoice_id: UUID) -> PurchaseInvoice:
        invoice = await self.repo.get_or_404(invoice_id)
        if invoice.status == InvoiceStatus.paid:
            raise InvoiceAlreadyMatchedException("Paid invoices cannot be disputed")
        invoice = await self.repo.update(invoice, status=InvoiceStatus.disputed)
        await self.session.commit()
        return invoice

    async def list_by_order(self, order_id: UUID) -> list[PurchaseInvoice]:
        await self.order_repo.get_or_404(order_id)
        return await self.repo.list_by_order(order_id)
