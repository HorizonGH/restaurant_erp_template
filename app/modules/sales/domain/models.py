from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.shared.domain.entities import BaseEntity
from app.modules.sales.domain.enums import SalesChannel, SalesOrderStatus


class SalesOrder(BaseEntity):
    __tablename__ = "sales_orders"
    __table_args__ = (
        Index("ix_sales_orders_status", "status"),
        Index("ix_sales_orders_channel", "channel"),
        Index("ix_sales_orders_source_location_id", "source_location_id"),
    )

    order_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    # Location from which ingredients are deducted when order is delivered
    source_location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    channel: Mapped[SalesChannel] = mapped_column(nullable=False)
    status: Mapped[SalesOrderStatus] = mapped_column(
        nullable=False, default=SalesOrderStatus.pending
    )
    # Optional table/seat reference (dine-in)
    table_reference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Stored total — updated whenever lines change
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )

    lines: Mapped[list[SalesOrderLine]] = relationship(
        "SalesOrderLine", back_populates="order", cascade="all, delete-orphan"
    )


class SalesOrderLine(BaseEntity):
    __tablename__ = "sales_order_lines"
    __table_args__ = (
        UniqueConstraint("order_id", "ingredient_id", name="uq_sales_order_line"),
        Index("ix_sales_order_lines_order_id", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_orders.entity_id", ondelete="CASCADE"),
        nullable=False,
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    @property
    def line_total(self) -> Decimal:
        return self.quantity * self.unit_price

    order: Mapped[SalesOrder] = relationship("SalesOrder", back_populates="lines")
