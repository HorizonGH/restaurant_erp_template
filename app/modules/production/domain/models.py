from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Date, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.shared.domain.entities import BaseEntity
from app.modules.production.domain.enums import ProductionOrderStatus


class Recipe(BaseEntity):
    __tablename__ = "recipes"
    __table_args__ = (
        Index("ix_recipes_name", "name"),
    )

    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Bumped on every PATCH so clients can detect concurrent edits
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # What this recipe produces
    yield_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    yield_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units_of_measure.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    # The ingredient that this recipe produces (optional — not all recipes produce a tracked ingredient)
    output_ingredient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.entity_id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    ingredients: Mapped[list[RecipeIngredient]] = relationship(
        "RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan"
    )
    production_orders: Mapped[list[ProductionOrder]] = relationship(
        "ProductionOrder", back_populates="recipe"
    )


class RecipeIngredient(BaseEntity):
    __tablename__ = "recipe_ingredients"
    __table_args__ = (
        UniqueConstraint("recipe_id", "ingredient_id", name="uq_recipe_ingredient"),
        Index("ix_recipe_ingredients_recipe_id", "recipe_id"),
    )

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.entity_id", ondelete="CASCADE"),
        nullable=False,
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_of_measure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units_of_measure.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="ingredients")


class ProductionOrder(BaseEntity):
    __tablename__ = "production_orders"
    __table_args__ = (
        Index("ix_production_orders_recipe_id", "recipe_id"),
        Index("ix_production_orders_status", "status"),
        Index("ix_production_orders_source_location_id", "source_location_id"),
    )

    order_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Location from which ingredients are consumed
    source_location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[ProductionOrderStatus] = mapped_column(
        nullable=False, default=ProductionOrderStatus.draft
    )
    # How many recipe yields to produce (multiplier applied to recipe quantities)
    quantity_to_produce: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False
    )
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="production_orders")
    lines: Mapped[list[ProductionOrderLine]] = relationship(
        "ProductionOrderLine", back_populates="order", cascade="all, delete-orphan"
    )
    yield_record: Mapped[YieldRecord | None] = relationship(
        "YieldRecord", back_populates="order", uselist=False
    )


class ProductionOrderLine(BaseEntity):
    __tablename__ = "production_order_lines"
    __table_args__ = (
        UniqueConstraint("order_id", "ingredient_id", name="uq_production_order_line"),
        Index("ix_production_order_lines_order_id", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("production_orders.entity_id", ondelete="CASCADE"),
        nullable=False,
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Quantity required = recipe_ingredient.quantity × quantity_to_produce
    required_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    # Actual quantity consumed (set on completion)
    consumed_quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )
    # Stock available at the time the order was confirmed
    available_quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )

    @property
    def is_available(self) -> bool:
        return self.available_quantity >= self.required_quantity

    @property
    def shortage(self) -> Decimal:
        return max(Decimal("0"), self.required_quantity - self.available_quantity)

    order: Mapped[ProductionOrder] = relationship(
        "ProductionOrder", back_populates="lines"
    )


class YieldRecord(BaseEntity):
    __tablename__ = "yield_records"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("production_orders.entity_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    expected_yield: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    actual_yield: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def variance(self) -> Decimal:
        return self.actual_yield - self.expected_yield

    @property
    def variance_percentage(self) -> Decimal:
        if self.expected_yield == Decimal("0"):
            return Decimal("0")
        return (self.variance / self.expected_yield * 100).quantize(Decimal("0.01"))

    order: Mapped[ProductionOrder] = relationship(
        "ProductionOrder", back_populates="yield_record"
    )
