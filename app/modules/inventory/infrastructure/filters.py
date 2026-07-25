from sqlalchemy_filterset import OrderingField

from app.core.shared.infrastructure.filters import (
    BaseFilterSet,
    BooleanFilter,
    Filter,
    NullsPosition,
    OrderingFilter,
)
from app.modules.inventory.domain.models import (
    Batch,
    KardexEntry,
    Location,
    StockItem,
    StockMovement,
)


class LocationFilterSet(BaseFilterSet[Location]):
    location_type = Filter(Location.location_type)
    is_active = BooleanFilter(Location.is_active)
    ordering = OrderingFilter(
        fields={
            "name": OrderingField(Location.name),
            "created_at": OrderingField(Location.created_at, nulls=NullsPosition.last),
        }
    )


class StockItemFilterSet(BaseFilterSet[StockItem]):
    location_id = Filter(StockItem.location_id)
    ingredient_id = Filter(StockItem.ingredient_id)
    ordering = OrderingFilter(
        fields={
            "created_at": OrderingField(StockItem.created_at, nulls=NullsPosition.last),
        }
    )


class BatchFilterSet(BaseFilterSet[Batch]):
    ingredient_id = Filter(Batch.ingredient_id)
    location_id = Filter(Batch.location_id)
    supplier_id = Filter(Batch.supplier_id)
    ordering = OrderingFilter(
        fields={
            "received_date": OrderingField(Batch.received_date, nulls=NullsPosition.last),
            "expiry_date": OrderingField(Batch.expiry_date, nulls=NullsPosition.last),
            "created_at": OrderingField(Batch.created_at, nulls=NullsPosition.last),
        }
    )


class StockMovementFilterSet(BaseFilterSet[StockMovement]):
    ingredient_id = Filter(StockMovement.ingredient_id)
    location_id = Filter(StockMovement.location_id)
    movement_type = Filter(StockMovement.movement_type)
    reference_type = Filter(StockMovement.reference_type)
    ordering = OrderingFilter(
        fields={
            "created_at": OrderingField(StockMovement.created_at, nulls=NullsPosition.last),
        }
    )


class KardexFilterSet(BaseFilterSet[KardexEntry]):
    ingredient_id = Filter(KardexEntry.ingredient_id)
    location_id = Filter(KardexEntry.location_id)
    movement_type = Filter(KardexEntry.movement_type)
    ordering = OrderingFilter(
        fields={
            "movement_date": OrderingField(KardexEntry.movement_date, nulls=NullsPosition.last),
        }
    )
