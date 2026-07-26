from __future__ import annotations

from sqlalchemy_filterset import OrderingField

from app.core.shared.infrastructure.filters import (
    BaseFilterSet,
    Filter,
    NullsPosition,
    OrderingFilter,
)
from app.modules.transfers.domain.models import PhysicalCount, PhysicalCountLine, Transfer, TransferLine


class TransferFilterSet(BaseFilterSet[Transfer]):
    from_location_id = Filter(Transfer.from_location_id)
    to_location_id = Filter(Transfer.to_location_id)
    status = Filter(Transfer.status)
    ordering = OrderingFilter(
        fields={
            "created_at": OrderingField(Transfer.created_at, nulls=NullsPosition.last),
        }
    )


class TransferLineFilterSet(BaseFilterSet[TransferLine]):
    transfer_id = Filter(TransferLine.transfer_id)
    ingredient_id = Filter(TransferLine.ingredient_id)
    ordering = OrderingFilter(
        fields={
            "created_at": OrderingField(TransferLine.created_at, nulls=NullsPosition.last),
        }
    )


class PhysicalCountFilterSet(BaseFilterSet[PhysicalCount]):
    location_id = Filter(PhysicalCount.location_id)
    status = Filter(PhysicalCount.status)
    ordering = OrderingFilter(
        fields={
            "created_at": OrderingField(PhysicalCount.created_at, nulls=NullsPosition.last),
        }
    )


class PhysicalCountLineFilterSet(BaseFilterSet[PhysicalCountLine]):
    count_id = Filter(PhysicalCountLine.count_id)
    ingredient_id = Filter(PhysicalCountLine.ingredient_id)
    ordering = OrderingFilter(
        fields={
            "created_at": OrderingField(PhysicalCountLine.created_at, nulls=NullsPosition.last),
        }
    )
