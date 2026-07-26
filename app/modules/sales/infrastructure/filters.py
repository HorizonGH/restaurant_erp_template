from __future__ import annotations

from sqlalchemy_filterset import OrderingField

from app.core.shared.infrastructure.filters import (
    BaseFilterSet,
    Filter,
    NullsPosition,
    OrderingFilter,
)
from app.modules.sales.domain.models import SalesOrder, SalesOrderLine


class SalesOrderFilterSet(BaseFilterSet[SalesOrder]):
    source_location_id = Filter(SalesOrder.source_location_id)
    channel = Filter(SalesOrder.channel)
    status = Filter(SalesOrder.status)
    ordering = OrderingFilter(
        fields={
            "created_at": OrderingField(SalesOrder.created_at, nulls=NullsPosition.last),
        }
    )


class SalesOrderLineFilterSet(BaseFilterSet[SalesOrderLine]):
    order_id = Filter(SalesOrderLine.order_id)
    ingredient_id = Filter(SalesOrderLine.ingredient_id)
    ordering = OrderingFilter(
        fields={
            "created_at": OrderingField(SalesOrderLine.created_at, nulls=NullsPosition.last),
        }
    )
