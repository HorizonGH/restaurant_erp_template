from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.core.shared.application.validators import StrippedStr
from app.core.shared.presentation.schemas import BaseInputSchema, BaseOutputSchema
from app.modules.catalog.domain.enums import UnitType


# --- Category ---

class CategoryCreateInput(BaseInputSchema):
    name: StrippedStr = Field(max_length=100)
    description: str | None = None
    parent_id: UUID | None = None


class CategoryUpdateInput(BaseInputSchema):
    name: StrippedStr | None = Field(default=None, max_length=100)
    description: str | None = None
    parent_id: UUID | None = None


class CategoryOutput(BaseOutputSchema):
    name: str
    description: str | None
    parent_id: UUID | None


# --- UnitOfMeasure ---

class UnitOfMeasureCreateInput(BaseInputSchema):
    name: StrippedStr = Field(max_length=100)
    abbreviation: StrippedStr = Field(max_length=20)
    unit_type: UnitType
    base_unit_id: UUID | None = None
    conversion_factor: Decimal | None = None


class UnitOfMeasureUpdateInput(BaseInputSchema):
    name: StrippedStr | None = Field(default=None, max_length=100)
    abbreviation: StrippedStr | None = Field(default=None, max_length=20)
    unit_type: UnitType | None = None
    base_unit_id: UUID | None = None
    conversion_factor: Decimal | None = None


class UnitOfMeasureOutput(BaseOutputSchema):
    name: str
    abbreviation: str
    unit_type: UnitType
    base_unit_id: UUID | None
    conversion_factor: Decimal | None


# --- Ingredient ---

class IngredientCreateInput(BaseInputSchema):
    sku: StrippedStr = Field(max_length=100)
    name: StrippedStr = Field(max_length=200)
    description: str | None = None
    category_id: UUID
    unit_of_measure_id: UUID
    reorder_point: Decimal = Field(default=Decimal("0"), ge=0)
    reorder_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    cost_per_unit: Decimal = Field(default=Decimal("0"), ge=0)
    is_active: bool = True
    allergen_info: str | None = None


class IngredientUpdateInput(BaseInputSchema):
    name: StrippedStr | None = Field(default=None, max_length=200)
    description: str | None = None
    category_id: UUID | None = None
    unit_of_measure_id: UUID | None = None
    reorder_point: Decimal | None = Field(default=None, ge=0)
    reorder_quantity: Decimal | None = Field(default=None, ge=0)
    cost_per_unit: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None
    allergen_info: str | None = None


class IngredientOutput(BaseOutputSchema):
    sku: str
    name: str
    description: str | None
    category_id: UUID
    unit_of_measure_id: UUID
    reorder_point: Decimal
    reorder_quantity: Decimal
    cost_per_unit: Decimal
    is_active: bool
    allergen_info: str | None


class IngredientDetailOutput(IngredientOutput):
    category: CategoryOutput
    unit_of_measure: UnitOfMeasureOutput


# --- Supplier ---

class SupplierCreateInput(BaseInputSchema):
    name: StrippedStr = Field(max_length=200)
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None
    is_active: bool = True


class SupplierUpdateInput(BaseInputSchema):
    name: StrippedStr | None = Field(default=None, max_length=200)
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None
    is_active: bool | None = None


class SupplierOutput(BaseOutputSchema):
    name: str
    contact_name: str | None
    email: str | None
    phone: str | None
    address: str | None
    tax_id: str | None
    is_active: bool


# --- SupplierIngredient ---

class SupplierIngredientLinkInput(BaseInputSchema):
    supplier_sku: str | None = None
    unit_cost: Decimal | None = Field(default=None, ge=0)


class SupplierIngredientOutput(BaseOutputSchema):
    supplier_id: UUID
    ingredient_id: UUID
    supplier_sku: str | None
    unit_cost: Decimal | None
