from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.core.shared.infrastructure.repository import BaseRepository
from app.modules.transfers.domain.models import (
    PhysicalCount,
    PhysicalCountLine,
    Transfer,
    TransferLine,
)


class TransferRepository(BaseRepository[Transfer]):
    model = Transfer

    async def get_by_number(self, transfer_number: str) -> Transfer | None:
        result = await self.session.execute(
            select(Transfer).where(
                Transfer.transfer_number == transfer_number,
                Transfer.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()


class TransferLineRepository(BaseRepository[TransferLine]):
    model = TransferLine

    async def list_by_transfer(self, transfer_id: UUID) -> list[TransferLine]:
        result = await self.session.execute(
            select(TransferLine).where(
                TransferLine.transfer_id == transfer_id,
                TransferLine.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())

    async def get_by_transfer_and_ingredient(
        self, transfer_id: UUID, ingredient_id: UUID
    ) -> TransferLine | None:
        result = await self.session.execute(
            select(TransferLine).where(
                TransferLine.transfer_id == transfer_id,
                TransferLine.ingredient_id == ingredient_id,
                TransferLine.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()


class PhysicalCountRepository(BaseRepository[PhysicalCount]):
    model = PhysicalCount


class PhysicalCountLineRepository(BaseRepository[PhysicalCountLine]):
    model = PhysicalCountLine

    async def list_by_count(self, count_id: UUID) -> list[PhysicalCountLine]:
        result = await self.session.execute(
            select(PhysicalCountLine).where(
                PhysicalCountLine.count_id == count_id,
                PhysicalCountLine.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())

    async def get_by_count_and_ingredient(
        self, count_id: UUID, ingredient_id: UUID
    ) -> PhysicalCountLine | None:
        result = await self.session.execute(
            select(PhysicalCountLine).where(
                PhysicalCountLine.count_id == count_id,
                PhysicalCountLine.ingredient_id == ingredient_id,
                PhysicalCountLine.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()
