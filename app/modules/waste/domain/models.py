from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.shared.domain.entities import BaseEntity


class WasteCategory(BaseEntity):
    __tablename__ = "waste_categories"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    records: Mapped[list[WasteRecord]] = relationship(
        "WasteRecord", back_populates="category"
    )


class WasteRecord(BaseEntity):
    __tablename__ = "waste_records"
    __table_args__ = (
        Index("ix_waste_records_ingredient_id", "ingredient_id"),
        Index("ix_waste_records_location_id", "location_id"),
        Index("ix_waste_records_category_id", "waste_category_id"),
        Index("ix_waste_records_waste_date", "waste_date"),
    )

    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    waste_category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("waste_categories.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    # FK to the inventory stock movement created when waste was recorded
    movement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_movements.entity_id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    waste_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def total_cost(self) -> Decimal:
        return self.quantity * self.unit_cost

    category: Mapped[WasteCategory] = relationship(
        "WasteCategory", back_populates="records"
    )
