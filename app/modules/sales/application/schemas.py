from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.core.shared.application.validators import StrippedStr
from app.core.shared.presentation.schemas import BaseInputSchema, BaseOutputSchema
from app.modules.sales.domain.enums import SalesChannel, SalesOrderStatus


class SalesOrderCreateInput(BaseInputSchema):
    source_location_id: UUID
    channel: SalesChannel
    table_reference: str | None = None
    notes: str | None = None


class SalesOrderUpdateInput(BaseInputSchema):
    table_reference: str | None = None
    notes: str | None = None


class SalesOrderOutput(BaseOutputSchema):
    order_number: str
    source_location_id: UUID
    channel: SalesChannel
    status: SalesOrderStatus
    table_reference: str | None
    notes: str | None
    total_amount: Decimal


class SalesOrderLineCreateInput(BaseInputSchema):
    ingredient_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class SalesOrderLineUpdateInput(BaseInputSchema):
    quantity: Decimal | None = Field(default=None, gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)


class SalesOrderLineOutput(BaseOutputSchema):
    order_id: UUID
    ingredient_id: UUID
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
