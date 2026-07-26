from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.core.shared.application.validators import StrippedStr
from app.core.shared.presentation.schemas import BaseInputSchema, BaseOutputSchema
from app.modules.production.domain.enums import ProductionOrderStatus


# ---------------------------------------------------------------------------
# Recipe
# ---------------------------------------------------------------------------

class RecipeCreateInput(BaseInputSchema):
    name: StrippedStr = Field(max_length=200)
    description: str | None = None
    yield_quantity: Decimal = Field(gt=0)
    yield_unit_id: UUID
    output_ingredient_id: UUID | None = None
    is_active: bool = True
    notes: str | None = None


class RecipeUpdateInput(BaseInputSchema):
    name: StrippedStr | None = Field(default=None, max_length=200)
    description: str | None = None
    yield_quantity: Decimal | None = Field(default=None, gt=0)
    yield_unit_id: UUID | None = None
    output_ingredient_id: UUID | None = None
    is_active: bool | None = None
    notes: str | None = None


class RecipeOutput(BaseOutputSchema):
    name: str
    description: str | None
    version: int
    yield_quantity: Decimal
    yield_unit_id: UUID
    output_ingredient_id: UUID | None
    is_active: bool
    notes: str | None


# ---------------------------------------------------------------------------
# Recipe Ingredient
# ---------------------------------------------------------------------------

class RecipeIngredientCreateInput(BaseInputSchema):
    ingredient_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_of_measure_id: UUID
    notes: str | None = None


class RecipeIngredientUpdateInput(BaseInputSchema):
    quantity: Decimal | None = Field(default=None, gt=0)
    unit_of_measure_id: UUID | None = None
    notes: str | None = None


class RecipeIngredientOutput(BaseOutputSchema):
    recipe_id: UUID
    ingredient_id: UUID
    quantity: Decimal
    unit_of_measure_id: UUID
    notes: str | None


# ---------------------------------------------------------------------------
# Production Order
# ---------------------------------------------------------------------------

class ProductionOrderCreateInput(BaseInputSchema):
    recipe_id: UUID
    source_location_id: UUID
    quantity_to_produce: Decimal = Field(gt=0)
    scheduled_date: date | None = None
    notes: str | None = None


class ProductionOrderUpdateInput(BaseInputSchema):
    quantity_to_produce: Decimal | None = Field(default=None, gt=0)
    scheduled_date: date | None = None
    notes: str | None = None


class ProductionOrderOutput(BaseOutputSchema):
    order_number: str
    recipe_id: UUID
    source_location_id: UUID
    status: ProductionOrderStatus
    quantity_to_produce: Decimal
    scheduled_date: date | None
    started_at: datetime | None
    completed_at: datetime | None
    notes: str | None


# ---------------------------------------------------------------------------
# Production Order Line
# ---------------------------------------------------------------------------

class ProductionOrderLineOutput(BaseOutputSchema):
    order_id: UUID
    ingredient_id: UUID
    required_quantity: Decimal
    consumed_quantity: Decimal
    available_quantity: Decimal
    is_available: bool
    shortage: Decimal


# ---------------------------------------------------------------------------
# Yield Record
# ---------------------------------------------------------------------------

class CompleteOrderInput(BaseInputSchema):
    actual_yield: Decimal = Field(gt=0)
    notes: str | None = None


class YieldRecordOutput(BaseOutputSchema):
    order_id: UUID
    expected_yield: Decimal
    actual_yield: Decimal
    variance: Decimal
    variance_percentage: Decimal
    notes: str | None


# ---------------------------------------------------------------------------
# Availability check response
# ---------------------------------------------------------------------------

class IngredientAvailabilityOutput(BaseInputSchema):
    ingredient_id: UUID
    required_quantity: Decimal
    available_quantity: Decimal
    is_available: bool
    shortage: Decimal


class OrderAvailabilityOutput(BaseInputSchema):
    order_id: UUID
    all_available: bool
    lines: list[IngredientAvailabilityOutput]
