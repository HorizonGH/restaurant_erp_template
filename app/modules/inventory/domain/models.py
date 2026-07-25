import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.shared.domain.entities import BaseEntity
from app.modules.inventory.domain.enums import LocationType, MovementType


class Location(BaseEntity):
    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    location_type: Mapped[LocationType] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    stock_items: Mapped[list["StockItem"]] = relationship(
        "StockItem", back_populates="location"
    )
    batches: Mapped[list["Batch"]] = relationship("Batch", back_populates="location")


class StockItem(BaseEntity):
    __tablename__ = "stock_items"
    __table_args__ = (
        UniqueConstraint("ingredient_id", "location_id", name="uq_stock_item"),
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
    quantity_on_hand: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )
    quantity_reserved: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )

    @property
    def quantity_available(self) -> Decimal:
        return self.quantity_on_hand - self.quantity_reserved

    location: Mapped[Location] = relationship("Location", back_populates="stock_items")


class Batch(BaseEntity):
    __tablename__ = "batches"
    __table_args__ = (
        Index("ix_batches_ingredient_location_expiry", "ingredient_id", "location_id", "expiry_date"),
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
    batch_number: Mapped[str] = mapped_column(String(100), nullable=False)
    lot_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.entity_id", ondelete="SET NULL"),
        nullable=True,
    )

    location: Mapped[Location] = relationship("Location", back_populates="batches")


class StockMovement(BaseEntity):
    __tablename__ = "stock_movements"
    __table_args__ = (
        Index("ix_stock_movements_ingredient_location", "ingredient_id", "location_id"),
        Index("ix_stock_movements_type", "movement_type"),
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
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.entity_id", ondelete="SET NULL"),
        nullable=True,
    )
    movement_type: Mapped[MovementType] = mapped_column(nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    batch: Mapped["Batch | None"] = relationship("Batch")


class KardexEntry(BaseEntity):
    __tablename__ = "kardex_entries"
    __table_args__ = (
        Index(
            "ix_kardex_ingredient_location_date",
            "ingredient_id",
            "location_id",
            "movement_date",
        ),
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
    movement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_movements.entity_id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    movement_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    movement_type: Mapped[MovementType] = mapped_column(nullable=False)
    quantity_in: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )
    quantity_out: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )
    quantity_balance: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    total_value_change: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    balance_value: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)

    movement: Mapped[StockMovement] = relationship("StockMovement")
