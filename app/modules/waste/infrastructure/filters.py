from __future__ import annotations

from sqlalchemy_filterset import OrderingField, SearchFilter

from app.core.shared.infrastructure.filters import (
    BaseFilterSet,
    Filter,
    NullsPosition,
    OrderingFilter,
    RangeFilter,
)
from app.modules.waste.domain.models import WasteCategory, WasteRecord


class WasteCategoryFilterSet(BaseFilterSet[WasteCategory]):
    name = SearchFilter(WasteCategory.name)
    ordering = OrderingFilter(
        fields={
            "name": OrderingField(WasteCategory.name, nulls=NullsPosition.last),
            "created_at": OrderingField(WasteCategory.created_at, nulls=NullsPosition.last),
        }
    )


class WasteRecordFilterSet(BaseFilterSet[WasteRecord]):
    ingredient_id = Filter(WasteRecord.ingredient_id)
    location_id = Filter(WasteRecord.location_id)
    waste_category_id = Filter(WasteRecord.waste_category_id)
    waste_date = RangeFilter(WasteRecord.waste_date)
    ordering = OrderingFilter(
        fields={
            "waste_date": OrderingField(WasteRecord.waste_date, nulls=NullsPosition.last),
            "created_at": OrderingField(WasteRecord.created_at, nulls=NullsPosition.last),
        }
    )
