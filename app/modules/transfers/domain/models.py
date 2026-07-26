from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.shared.domain.entities import BaseEntity
from app.modules.transfers.domain.enums import PhysicalCountStatus, TransferStatus


class Transfer(BaseEntity):
    __tablename__ = "transfers"

    transfer_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    from_location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    to_location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[TransferStatus] = mapped_column(nullable=False, default=TransferStatus.draft)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    lines: Mapped[list[TransferLine]] = relationship(
        "TransferLine", back_populates="transfer", cascade="all, delete-orphan"
    )


class TransferLine(BaseEntity):
    __tablename__ = "transfer_lines"
    __table_args__ = (
        UniqueConstraint("transfer_id", "ingredient_id", name="uq_transfer_line"),
        Index("ix_transfer_lines_transfer_id", "transfer_id"),
    )

    transfer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transfers.entity_id", ondelete="CASCADE"),
        nullable=False,
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    # batch_id is optional — if set, deducts from that specific batch; otherwise FIFO
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.entity_id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    transferred_quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )

    transfer: Mapped[Transfer] = relationship("Transfer", back_populates="lines")


class PhysicalCount(BaseEntity):
    __tablename__ = "physical_counts"
    __table_args__ = (
        Index("ix_physical_counts_location_id", "location_id"),
    )

    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[PhysicalCountStatus] = mapped_column(
        nullable=False, default=PhysicalCountStatus.in_progress
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    lines: Mapped[list[PhysicalCountLine]] = relationship(
        "PhysicalCountLine", back_populates="count", cascade="all, delete-orphan"
    )


class PhysicalCountLine(BaseEntity):
    __tablename__ = "physical_count_lines"
    __table_args__ = (
        UniqueConstraint("count_id", "ingredient_id", name="uq_count_line"),
        Index("ix_physical_count_lines_count_id", "count_id"),
    )

    count_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("physical_counts.entity_id", ondelete="CASCADE"),
        nullable=False,
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.entity_id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Snapshot of system quantity at the moment the count was created
    system_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    # Filled in by staff during the physical count
    counted_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)

    @property
    def variance(self) -> Decimal | None:
        """counted - system; negative means less than expected (loss/shrinkage)."""
        if self.counted_quantity is None:
            return None
        return self.counted_quantity - self.system_quantity

    count: Mapped[PhysicalCount] = relationship("PhysicalCount", back_populates="lines")
