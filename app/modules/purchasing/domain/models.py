from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.shared.domain.entities import BaseEntity
from app.modules.purchasing.domain.enums import InvoiceStatus, POStatus, ReceiptStatus


class PurchaseOrder(BaseEntity):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        Index("ix_purchase_orders_supplier_id", "supplier_id"),
        Index("ix_purchase_orders_status", "status"),
    )

    po_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[POStatus] = mapped_column(nullable=False, default=POStatus.draft)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Computed and stored for reporting; updated whenever lines change
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )

    lines: Mapped[list[PurchaseOrderLine]] = relationship(
        "PurchaseOrderLine", back_populates="order", cascade="all, delete-orphan"
    )
    receipts: Mapped[list[GoodsReceipt]] = relationship(
        "GoodsReceipt", back_populates="order"
    )
    invoices: Mapped[list[PurchaseInvoice]] = relationship(
        "PurchaseInvoice", back_populates="order"
    )


class PurchaseOrderLine(BaseEntity):
    __tablename__ = "purchase_order_lines"
    __table_args__ = (
        UniqueConstraint("order_id", "ingredient_id", name="uq_po_line"),
        Index("ix_po_lines_order_id", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.entity_id", ondelete="CASCADE"),
        nullable=False,
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    ordered_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)

    @property
    def line_total(self) -> Decimal:
        return self.ordered_quantity * self.unit_cost

    @property
    def is_fully_received(self) -> bool:
        return self.received_quantity >= self.ordered_quantity

    order: Mapped[PurchaseOrder] = relationship("PurchaseOrder", back_populates="lines")


class GoodsReceipt(BaseEntity):
    __tablename__ = "goods_receipts"
    __table_args__ = (
        Index("ix_goods_receipts_order_id", "order_id"),
    )

    receipt_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    destination_location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[ReceiptStatus] = mapped_column(
        nullable=False, default=ReceiptStatus.draft
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    lines: Mapped[list[GoodsReceiptLine]] = relationship(
        "GoodsReceiptLine", back_populates="receipt", cascade="all, delete-orphan"
    )
    order: Mapped[PurchaseOrder] = relationship("PurchaseOrder", back_populates="receipts")


class GoodsReceiptLine(BaseEntity):
    __tablename__ = "goods_receipt_lines"
    __table_args__ = (
        UniqueConstraint("receipt_id", "ingredient_id", name="uq_receipt_line"),
        Index("ix_receipt_lines_receipt_id", "receipt_id"),
    )

    receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goods_receipts.entity_id", ondelete="CASCADE"),
        nullable=False,
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    batch_number: Mapped[str] = mapped_column(String(100), nullable=False)
    lot_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)

    @property
    def line_total(self) -> Decimal:
        return self.received_quantity * self.unit_cost

    receipt: Mapped[GoodsReceipt] = relationship("GoodsReceipt", back_populates="lines")


class PurchaseInvoice(BaseEntity):
    __tablename__ = "purchase_invoices"
    __table_args__ = (
        Index("ix_purchase_invoices_order_id", "order_id"),
    )

    invoice_number: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[InvoiceStatus] = mapped_column(
        nullable=False, default=InvoiceStatus.pending
    )
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped[PurchaseOrder] = relationship("PurchaseOrder", back_populates="invoices")
