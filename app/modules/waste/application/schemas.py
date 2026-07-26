from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.core.shared.application.validators import StrippedStr
from app.core.shared.presentation.schemas import BaseInputSchema, BaseOutputSchema


class WasteCategoryCreateInput(BaseInputSchema):
    name: StrippedStr = Field(max_length=100)
    description: str | None = None


class WasteCategoryUpdateInput(BaseInputSchema):
    name: StrippedStr | None = Field(default=None, max_length=100)
    description: str | None = None


class WasteCategoryOutput(BaseOutputSchema):
    name: str
    description: str | None


class WasteRecordCreateInput(BaseInputSchema):
    ingredient_id: UUID
    location_id: UUID
    waste_category_id: UUID
    quantity: Decimal = Field(gt=0)
    waste_date: date
    reason: str | None = None
    notes: str | None = None


class WasteRecordOutput(BaseOutputSchema):
    ingredient_id: UUID
    location_id: UUID
    waste_category_id: UUID
    movement_id: UUID
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    waste_date: date
    reason: str | None
    notes: str | None


class WasteSummaryLineOutput(BaseInputSchema):
    waste_category_id: UUID
    category_name: str
    total_quantity: Decimal
    total_cost: Decimal
    record_count: int
