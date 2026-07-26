from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.domain.exceptions import ConflictException, NotFoundException
from app.core.shared.domain.helpers import utcnow
from app.modules.catalog.infrastructure.repository import IngredientRepository
from app.modules.inventory.application.schemas import MovementAdjustmentInput, MovementExitInput
from app.modules.inventory.application.service import MovementService
from app.modules.inventory.domain.enums import MovementType
from app.modules.inventory.domain.exceptions import InsufficientStockException
from app.modules.inventory.infrastructure.repository import (
    KardexRepository,
    LocationRepository,
    StockItemRepository,
)
from app.modules.transfers.application.schemas import (
    PhysicalCountCreateInput,
    PhysicalCountLineRecordInput,
    PhysicalCountUpdateInput,
    TransferCreateInput,
    TransferLineCreateInput,
    TransferLineUpdateInput,
    TransferUpdateInput,
)
from app.modules.transfers.domain.enums import PhysicalCountStatus, TransferStatus
from app.modules.transfers.domain.exceptions import (
    EmptyPhysicalCountException,
    EmptyTransferException,
    PhysicalCountAlreadyCompletedException,
    PhysicalCountNotInProgressException,
    TransferAlreadyCancelledException,
    TransferAlreadyCompletedException,
    TransferNotDraftException,
    TransferNotInTransitException,
)
from app.modules.transfers.domain.models import (
    PhysicalCount,
    PhysicalCountLine,
    Transfer,
    TransferLine,
)
from app.modules.transfers.infrastructure.filters import (
    PhysicalCountFilterSet,
    PhysicalCountLineFilterSet,
    TransferFilterSet,
    TransferLineFilterSet,
)
from app.modules.transfers.infrastructure.repository import (
    PhysicalCountLineRepository,
    PhysicalCountRepository,
    TransferLineRepository,
    TransferRepository,
)


def _generate_transfer_number() -> str:
    from datetime import date
    today = date.today()
    suffix = uuid.uuid4().hex[:6].upper()
    return f"TRF-{today.strftime('%Y%m')}-{suffix}"


def _generate_count_number() -> str:
    from datetime import date
    today = date.today()
    suffix = uuid.uuid4().hex[:6].upper()
    return f"CNT-{today.strftime('%Y%m')}-{suffix}"


# ---------------------------------------------------------------------------
# TransferService
# ---------------------------------------------------------------------------

class TransferService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TransferRepository(session)
        self.line_repo = TransferLineRepository(session)
        self.location_repo = LocationRepository(session)
        self.ingredient_repo = IngredientRepository(session)
        self.stock_repo = StockItemRepository(session)
        self.movement_svc = MovementService(session)

    async def get(self, transfer_id: UUID) -> Transfer:
        return await self.repo.get_or_404(transfer_id)

    async def list(self, params: dict) -> tuple[Sequence[Transfer], int]:
        return await self.repo.list(TransferFilterSet, params)

    async def create(self, data: TransferCreateInput) -> Transfer:
        await self.location_repo.get_or_404(data.from_location_id)
        await self.location_repo.get_or_404(data.to_location_id)
        if data.from_location_id == data.to_location_id:
            raise ConflictException("Source and destination locations must be different")

        transfer_number = _generate_transfer_number()
        # Extremely unlikely collision — retry once
        if await self.repo.get_by_number(transfer_number) is not None:
            transfer_number = _generate_transfer_number()

        transfer = await self.repo.create(
            transfer_number=transfer_number,
            from_location_id=data.from_location_id,
            to_location_id=data.to_location_id,
            status=TransferStatus.draft,
            notes=data.notes,
        )
        await self.session.commit()
        return transfer

    async def update(self, transfer_id: UUID, data: TransferUpdateInput) -> Transfer:
        transfer = await self.repo.get_or_404(transfer_id)
        if transfer.status != TransferStatus.draft:
            raise TransferNotDraftException("Only draft transfers can be updated")
        transfer = await self.repo.update(transfer, notes=data.notes)
        await self.session.commit()
        return transfer

    async def add_line(self, transfer_id: UUID, data: TransferLineCreateInput) -> TransferLine:
        transfer = await self.repo.get_or_404(transfer_id)
        if transfer.status != TransferStatus.draft:
            raise TransferNotDraftException("Lines can only be added to draft transfers")

        await self.ingredient_repo.get_or_404(data.ingredient_id)

        existing = await self.line_repo.get_by_transfer_and_ingredient(
            transfer_id, data.ingredient_id
        )
        if existing is not None:
            raise ConflictException("This ingredient already has a line on this transfer")

        line = await self.line_repo.create(
            transfer_id=transfer_id,
            ingredient_id=data.ingredient_id,
            batch_id=data.batch_id,
            requested_quantity=data.requested_quantity,
            transferred_quantity=Decimal("0"),
        )
        await self.session.commit()
        return line

    async def update_line(
        self, transfer_id: UUID, line_id: UUID, data: TransferLineUpdateInput
    ) -> TransferLine:
        transfer = await self.repo.get_or_404(transfer_id)
        if transfer.status != TransferStatus.draft:
            raise TransferNotDraftException("Lines can only be updated on draft transfers")

        line = await self.line_repo.get_or_404(line_id)
        if line.transfer_id != transfer_id:
            raise NotFoundException("Transfer line not found on this transfer")

        values = data.model_dump(exclude_none=True)
        line = await self.line_repo.update(line, **values)
        await self.session.commit()
        return line

    async def remove_line(self, transfer_id: UUID, line_id: UUID) -> None:
        transfer = await self.repo.get_or_404(transfer_id)
        if transfer.status != TransferStatus.draft:
            raise TransferNotDraftException("Lines can only be removed from draft transfers")

        line = await self.line_repo.get_or_404(line_id)
        if line.transfer_id != transfer_id:
            raise NotFoundException("Transfer line not found on this transfer")

        await self.line_repo.soft_delete(line)
        await self.session.commit()

    async def send(self, transfer_id: UUID) -> Transfer:
        """
        Validate stock availability for all lines and transition to in_transit.
        Does NOT deduct stock yet — deduction happens on receive().
        """
        transfer = await self.repo.get_or_404(transfer_id)
        if transfer.status != TransferStatus.draft:
            raise TransferNotDraftException("Only draft transfers can be sent")

        lines = await self.line_repo.list_by_transfer(transfer_id)
        if not lines:
            raise EmptyTransferException("Transfer has no lines — add items before sending")

        # Pre-validate stock for all lines
        for line in lines:
            stock = await self.stock_repo.get_by_ingredient_and_location(
                line.ingredient_id, transfer.from_location_id
            )
            if stock is None or stock.quantity_available < line.requested_quantity:
                available = stock.quantity_available if stock else Decimal("0")
                raise InsufficientStockException(
                    f"Insufficient stock for ingredient {line.ingredient_id}: "
                    f"available={available}, requested={line.requested_quantity}"
                )

        transfer = await self.repo.update(transfer, status=TransferStatus.in_transit)
        await self.session.commit()
        return transfer

    async def receive(self, transfer_id: UUID) -> Transfer:
        """
        Deduct stock from source location and add to destination location
        for each line. Creates transfer_out and transfer_in movements.
        """
        transfer = await self.repo.get_or_404(transfer_id)
        if transfer.status != TransferStatus.in_transit:
            raise TransferNotInTransitException("Only in-transit transfers can be received")

        lines = await self.line_repo.list_by_transfer(transfer_id)

        for line in lines:
            # Exit from source (transfer_out)
            exit_movement = await self.movement_svc.record_exit(
                MovementExitInput(
                    ingredient_id=line.ingredient_id,
                    location_id=transfer.from_location_id,
                    quantity=line.requested_quantity,
                    reference_type="transfer",
                    reference_id=transfer.entity_id,
                    reason=f"Transfer {transfer.transfer_number} — outbound",
                ),
                movement_type=MovementType.transfer_out,
            )

            # Get the unit cost from the exit movement to use for the entry
            from app.modules.inventory.infrastructure.repository import KardexRepository
            kardex_repo = KardexRepository(self.session)
            unit_cost = await kardex_repo.get_last_unit_cost(
                line.ingredient_id, transfer.from_location_id
            )

            # Entry into destination (transfer_in)
            from app.modules.inventory.application.schemas import MovementEntryInput
            from datetime import date
            await self.movement_svc.record_entry(
                MovementEntryInput(
                    ingredient_id=line.ingredient_id,
                    location_id=transfer.to_location_id,
                    quantity=line.requested_quantity,
                    unit_cost=unit_cost,
                    batch_number=f"TRF-{transfer.transfer_number}",
                    received_date=date.today(),
                    reference_type="transfer",
                    reference_id=transfer.entity_id,
                    notes=f"Received from transfer {transfer.transfer_number}",
                ),
            )

            await self.line_repo.update(
                line, transferred_quantity=line.requested_quantity
            )

        transfer = await self.repo.update(transfer, status=TransferStatus.completed)
        await self.session.commit()
        return transfer

    async def cancel(self, transfer_id: UUID) -> Transfer:
        transfer = await self.repo.get_or_404(transfer_id)
        if transfer.status == TransferStatus.completed:
            raise TransferAlreadyCompletedException("Completed transfers cannot be cancelled")
        if transfer.status == TransferStatus.cancelled:
            raise TransferAlreadyCancelledException("Transfer is already cancelled")

        transfer = await self.repo.update(transfer, status=TransferStatus.cancelled)
        await self.session.commit()
        return transfer

    async def list_lines(self, transfer_id: UUID) -> list[TransferLine]:
        await self.repo.get_or_404(transfer_id)
        return await self.line_repo.list_by_transfer(transfer_id)


# ---------------------------------------------------------------------------
# PhysicalCountService
# ---------------------------------------------------------------------------

class PhysicalCountService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PhysicalCountRepository(session)
        self.line_repo = PhysicalCountLineRepository(session)
        self.location_repo = LocationRepository(session)
        self.ingredient_repo = IngredientRepository(session)
        self.stock_repo = StockItemRepository(session)
        self.movement_svc = MovementService(session)

    async def get(self, count_id: UUID) -> PhysicalCount:
        return await self.repo.get_or_404(count_id)

    async def list(self, params: dict) -> tuple[Sequence[PhysicalCount], int]:
        return await self.repo.list(PhysicalCountFilterSet, params)

    async def create(self, data: PhysicalCountCreateInput) -> PhysicalCount:
        """
        Create a new physical count and snapshot the current system stock
        quantities for all active stock items at the location (or a specified
        subset of ingredient_ids).
        """
        await self.location_repo.get_or_404(data.location_id)

        count = await self.repo.create(
            location_id=data.location_id,
            status=PhysicalCountStatus.in_progress,
            notes=data.notes,
        )

        # Snapshot current stock items at this location
        stock_items = await self.stock_repo.list_by_location(data.location_id)

        if data.ingredient_ids:
            id_set = set(data.ingredient_ids)
            stock_items = [s for s in stock_items if s.ingredient_id in id_set]

        for item in stock_items:
            await self.line_repo.create(
                count_id=count.entity_id,
                ingredient_id=item.ingredient_id,
                system_quantity=item.quantity_on_hand,
                counted_quantity=None,
            )

        await self.session.commit()
        return count

    async def update(self, count_id: UUID, data: PhysicalCountUpdateInput) -> PhysicalCount:
        count = await self.repo.get_or_404(count_id)
        if count.status != PhysicalCountStatus.in_progress:
            raise PhysicalCountNotInProgressException("Only in-progress counts can be updated")
        count = await self.repo.update(count, notes=data.notes)
        await self.session.commit()
        return count

    async def record_line(
        self, count_id: UUID, line_id: UUID, data: PhysicalCountLineRecordInput
    ) -> PhysicalCountLine:
        """Submit the physically counted quantity for one line."""
        count = await self.repo.get_or_404(count_id)
        if count.status != PhysicalCountStatus.in_progress:
            raise PhysicalCountNotInProgressException(
                "Counted quantities can only be recorded on in-progress counts"
            )

        line = await self.line_repo.get_or_404(line_id)
        if line.count_id != count_id:
            raise NotFoundException("Count line not found on this count")

        line = await self.line_repo.update(line, counted_quantity=data.counted_quantity)
        await self.session.commit()
        return line

    async def complete(self, count_id: UUID) -> PhysicalCount:
        """
        Apply variances as adjustment movements for every line where
        counted_quantity differs from system_quantity.
        Lines with counted_quantity=None are skipped (not counted yet).
        """
        count = await self.repo.get_or_404(count_id)
        if count.status == PhysicalCountStatus.completed:
            raise PhysicalCountAlreadyCompletedException("Count is already completed")
        if count.status != PhysicalCountStatus.in_progress:
            raise PhysicalCountNotInProgressException("Only in-progress counts can be completed")

        lines = await self.line_repo.list_by_count(count_id)
        counted_lines = [l for l in lines if l.counted_quantity is not None]

        if not counted_lines:
            raise EmptyPhysicalCountException(
                "No lines have been counted yet — record at least one counted quantity"
            )

        for line in counted_lines:
            variance = line.counted_quantity - line.system_quantity  # type: ignore[operator]
            if variance == Decimal("0"):
                continue

            await self.movement_svc.record_adjustment(
                MovementAdjustmentInput(
                    ingredient_id=line.ingredient_id,
                    location_id=count.location_id,
                    quantity_delta=variance,
                    reason=f"Physical count {count_id} — variance correction",
                    notes=(
                        f"System: {line.system_quantity}, "
                        f"Counted: {line.counted_quantity}, "
                        f"Variance: {variance:+}"
                    ),
                )
            )

        count = await self.repo.update(count, status=PhysicalCountStatus.completed)
        await self.session.commit()
        return count

    async def cancel(self, count_id: UUID) -> PhysicalCount:
        count = await self.repo.get_or_404(count_id)
        if count.status == PhysicalCountStatus.completed:
            raise PhysicalCountAlreadyCompletedException("Completed counts cannot be cancelled")
        if count.status != PhysicalCountStatus.in_progress:
            raise PhysicalCountNotInProgressException("Only in-progress counts can be cancelled")

        count = await self.repo.update(count, status=PhysicalCountStatus.cancelled)
        await self.session.commit()
        return count

    async def list_lines(self, count_id: UUID) -> list[PhysicalCountLine]:
        await self.repo.get_or_404(count_id)
        return await self.line_repo.list_by_count(count_id)
