from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import Field, computed_field

from app.core.shared.application.validators import StrippedStr
from app.core.shared.presentation.schemas import BaseInputSchema, BaseOutputSchema
from app.modules.purchasing.domain.enums import InvoiceStatus, POStatus, ReceiptStatus


# ---------------------------------------------------------------------------
# Purchase Order
# ---------------------------------------------------------------------------

class POCreateInput(BaseInputSchema):
    supplier_id: UUID
    expected_delivery_date: date | None = None
    notes: str | None = None


class POUpdateInput(BaseInputSchema):
    expected_delivery_date: date | None = None
    notes: str | None = None


class POOutput(BaseOutputSchema):
    po_number: str
    supplier_id: UUID
    status: POStatus
    expected_delivery_date: date | None
    notes: str | None
    total_amount: Decimal


# ---------------------------------------------------------------------------
# Purchase Order Line
# ---------------------------------------------------------------------------

class POLineCreateInput(BaseInputSchema):
    ingredient_id: UUID
    ordered_quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)


class POLineUpdateInput(BaseInputSchema):
    ordered_quantity: Decimal | None = Field(default=None, gt=0)
    unit_cost: Decimal | None = Field(default=None, ge=0)


class POLineOutput(BaseOutputSchema):
    order_id: UUID
    ingredient_id: UUID
    ordered_quantity: Decimal
    received_quantity: Decimal
    unit_cost: Decimal
    line_total: Decimal
    is_fully_received: bool


# ---------------------------------------------------------------------------
# Goods Receipt
# ---------------------------------------------------------------------------

class ReceiptCreateInput(BaseInputSchema):
    order_id: UUID
    destination_location_id: UUID
    notes: str | None = None


class ReceiptUpdateInput(BaseInputSchema):
    notes: str | None = None


class ReceiptOutput(BaseOutputSchema):
    receipt_number: str
    order_id: UUID
    destination_location_id: UUID
    status: ReceiptStatus
    notes: str | None


# ---------------------------------------------------------------------------
# Goods Receipt Line
# ---------------------------------------------------------------------------

class ReceiptLineCreateInput(BaseInputSchema):
    ingredient_id: UUID
    batch_number: StrippedStr = Field(max_length=100)
    lot_number: str | None = None
    expiry_date: date | None = None
    received_quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)


class ReceiptLineUpdateInput(BaseInputSchema):
    batch_number: StrippedStr | None = Field(default=None, max_length=100)
    lot_number: str | None = None
    expiry_date: date | None = None
    received_quantity: Decimal | None = Field(default=None, gt=0)
    unit_cost: Decimal | None = Field(default=None, ge=0)


class ReceiptLineOutput(BaseOutputSchema):
    receipt_id: UUID
    ingredient_id: UUID
    batch_number: str
    lot_number: str | None
    expiry_date: date | None
    received_quantity: Decimal
    unit_cost: Decimal
    line_total: Decimal


# ---------------------------------------------------------------------------
# Purchase Invoice
# ---------------------------------------------------------------------------

class InvoiceCreateInput(BaseInputSchema):
    order_id: UUID
    invoice_number: StrippedStr = Field(max_length=100)
    invoice_date: date
    due_date: date | None = None
    total_amount: Decimal = Field(ge=0)
    notes: str | None = None


class InvoiceUpdateInput(BaseInputSchema):
    due_date: date | None = None
    notes: str | None = None


class InvoiceOutput(BaseOutputSchema):
    invoice_number: str
    order_id: UUID
    status: InvoiceStatus
    invoice_date: date
    due_date: date | None
    total_amount: Decimal
    notes: str | None
