from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, computed_field

from app.core.shared.application.validators import StrippedStr
from app.core.shared.presentation.schemas import BaseInputSchema, BaseOutputSchema, BaseSchema
from app.modules.catalog.application.schemas import IngredientOutput
from app.modules.inventory.domain.enums import LocationType, MovementType


# --- Location ---

class LocationCreateInput(BaseInputSchema):
    name: StrippedStr = Field(max_length=200)
    code: StrippedStr = Field(max_length=50)
    location_type: LocationType
    description: str | None = None
    is_active: bool = True


class LocationUpdateInput(BaseInputSchema):
    name: StrippedStr | None = Field(default=None, max_length=200)
    code: StrippedStr | None = Field(default=None, max_length=50)
    location_type: LocationType | None = None
    description: str | None = None
    is_active: bool | None = None


class LocationOutput(BaseOutputSchema):
    name: str
    code: str
    location_type: LocationType
    description: str | None
    is_active: bool


class LocationSelectOutput(BaseSchema):
    entity_id: UUID
    name: str
    code: str


# --- StockItem ---

class StockItemOutput(BaseOutputSchema):
    ingredient_id: UUID
    location_id: UUID
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    quantity_available: Decimal


class StockItemDetailOutput(StockItemOutput):
    ingredient: IngredientOutput
    location: LocationOutput


# --- Batch ---

class BatchCreateInput(BaseInputSchema):
    ingredient_id: UUID
    location_id: UUID
    batch_number: StrippedStr = Field(max_length=100)
    lot_number: str | None = None
    quantity: Decimal = Field(ge=0)
    expiry_date: date | None = None
    received_date: date
    unit_cost: Decimal = Field(ge=0)
    supplier_id: UUID | None = None


class BatchUpdateInput(BaseInputSchema):
    lot_number: str | None = None
    quantity: Decimal | None = Field(default=None, ge=0)
    expiry_date: date | None = None


class BatchOutput(BaseOutputSchema):
    ingredient_id: UUID
    location_id: UUID
    batch_number: str
    lot_number: str | None
    quantity: Decimal
    expiry_date: date | None
    received_date: date
    unit_cost: Decimal
    supplier_id: UUID | None


# --- Stock Movements ---

class MovementEntryInput(BaseInputSchema):
    ingredient_id: UUID
    location_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)
    batch_number: StrippedStr = Field(max_length=100)
    lot_number: str | None = None
    expiry_date: date | None = None
    received_date: date
    supplier_id: UUID | None = None
    reference_type: str | None = None
    reference_id: UUID | None = None
    notes: str | None = None


class MovementExitInput(BaseInputSchema):
    ingredient_id: UUID
    location_id: UUID
    quantity: Decimal = Field(gt=0)
    reference_type: str | None = None
    reference_id: UUID | None = None
    reason: str | None = None
    notes: str | None = None


class MovementAdjustmentInput(BaseInputSchema):
    ingredient_id: UUID
    location_id: UUID
    quantity_delta: Decimal
    reason: StrippedStr
    notes: str | None = None
    unit_cost: Decimal | None = Field(default=None, ge=0)


class StockMovementOutput(BaseOutputSchema):
    ingredient_id: UUID
    location_id: UUID
    batch_id: UUID | None
    movement_type: MovementType
    quantity: Decimal
    unit_cost: Decimal
    reference_type: str | None
    reference_id: UUID | None
    reason: str | None
    notes: str | None
    performed_by: UUID | None


# --- Kardex ---

class KardexEntryOutput(BaseOutputSchema):
    ingredient_id: UUID
    location_id: UUID
    movement_id: UUID
    movement_date: datetime
    movement_type: MovementType
    quantity_in: Decimal
    quantity_out: Decimal
    quantity_balance: Decimal
    unit_cost: Decimal
    total_value_change: Decimal
    balance_value: Decimal
