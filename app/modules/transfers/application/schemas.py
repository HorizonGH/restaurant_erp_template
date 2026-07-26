from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.core.shared.application.validators import StrippedStr
from app.core.shared.presentation.schemas import BaseInputSchema, BaseOutputSchema
from app.modules.transfers.domain.enums import PhysicalCountStatus, TransferStatus


# ---------------------------------------------------------------------------
# Transfer
# ---------------------------------------------------------------------------

class TransferCreateInput(BaseInputSchema):
    from_location_id: UUID
    to_location_id: UUID
    notes: str | None = None


class TransferUpdateInput(BaseInputSchema):
    notes: str | None = None


class TransferOutput(BaseOutputSchema):
    transfer_number: str
    from_location_id: UUID
    to_location_id: UUID
    status: TransferStatus
    notes: str | None


# ---------------------------------------------------------------------------
# TransferLine
# ---------------------------------------------------------------------------

class TransferLineCreateInput(BaseInputSchema):
    ingredient_id: UUID
    requested_quantity: Decimal = Field(gt=0)
    batch_id: UUID | None = None


class TransferLineUpdateInput(BaseInputSchema):
    requested_quantity: Decimal | None = Field(default=None, gt=0)
    batch_id: UUID | None = None


class TransferLineOutput(BaseOutputSchema):
    transfer_id: UUID
    ingredient_id: UUID
    batch_id: UUID | None
    requested_quantity: Decimal
    transferred_quantity: Decimal


# ---------------------------------------------------------------------------
# Physical Count
# ---------------------------------------------------------------------------

class PhysicalCountCreateInput(BaseInputSchema):
    location_id: UUID
    notes: str | None = None
    # If provided, snapshot is pre-populated for these ingredients only.
    # If empty, the service snapshots ALL active stock items at the location.
    ingredient_ids: list[UUID] | None = None


class PhysicalCountUpdateInput(BaseInputSchema):
    notes: str | None = None


class PhysicalCountOutput(BaseOutputSchema):
    location_id: UUID
    status: PhysicalCountStatus
    notes: str | None


# ---------------------------------------------------------------------------
# PhysicalCountLine
# ---------------------------------------------------------------------------

class PhysicalCountLineRecordInput(BaseInputSchema):
    """Used to submit a counted quantity for one line."""
    counted_quantity: Decimal = Field(ge=0)


class PhysicalCountLineOutput(BaseOutputSchema):
    count_id: UUID
    ingredient_id: UUID
    system_quantity: Decimal
    counted_quantity: Decimal | None
    variance: Decimal | None
