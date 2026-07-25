import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.shared.domain.entities import BaseEntity
from app.modules.catalog.domain.enums import UnitType


class Category(BaseEntity):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.entity_id", ondelete="RESTRICT"),
        nullable=True,
    )

    parent: Mapped["Category | None"] = relationship(
        "Category", remote_side="Category.entity_id", back_populates="children"
    )
    children: Mapped[list["Category"]] = relationship(
        "Category", back_populates="parent"
    )
    ingredients: Mapped[list["Ingredient"]] = relationship(
        "Ingredient", back_populates="category"
    )


class UnitOfMeasure(BaseEntity):
    __tablename__ = "units_of_measure"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    abbreviation: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    unit_type: Mapped[UnitType] = mapped_column(nullable=False)
    base_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units_of_measure.entity_id", ondelete="RESTRICT"),
        nullable=True,
    )
    conversion_factor: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 10), nullable=True
    )

    base_unit: Mapped["UnitOfMeasure | None"] = relationship(
        "UnitOfMeasure",
        remote_side="UnitOfMeasure.entity_id",
        back_populates="derived_units",
    )
    derived_units: Mapped[list["UnitOfMeasure"]] = relationship(
        "UnitOfMeasure", back_populates="base_unit"
    )
    ingredients: Mapped[list["Ingredient"]] = relationship(
        "Ingredient", back_populates="unit_of_measure"
    )


class Ingredient(BaseEntity):
    __tablename__ = "ingredients"

    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    unit_of_measure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units_of_measure.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    reorder_point: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0")
    )
    reorder_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0")
    )
    cost_per_unit: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0")
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    allergen_info: Mapped[str | None] = mapped_column(Text, nullable=True)

    category: Mapped[Category] = relationship("Category", back_populates="ingredients")
    unit_of_measure: Mapped[UnitOfMeasure] = relationship(
        "UnitOfMeasure", back_populates="ingredients"
    )
    supplier_links: Mapped[list["SupplierIngredient"]] = relationship(
        "SupplierIngredient", back_populates="ingredient", cascade="all, delete-orphan"
    )


class Supplier(BaseEntity):
    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    ingredient_links: Mapped[list["SupplierIngredient"]] = relationship(
        "SupplierIngredient", back_populates="supplier", cascade="all, delete-orphan"
    )


class SupplierIngredient(BaseEntity):
    __tablename__ = "supplier_ingredients"
    __table_args__ = (
        UniqueConstraint("supplier_id", "ingredient_id", name="uq_supplier_ingredient"),
    )

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.entity_id", ondelete="CASCADE"),
        nullable=False,
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.entity_id", ondelete="CASCADE"),
        nullable=False,
    )
    supplier_sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    supplier: Mapped[Supplier] = relationship(
        "Supplier", back_populates="ingredient_links"
    )
    ingredient: Mapped[Ingredient] = relationship(
        "Ingredient", back_populates="supplier_links"
    )
