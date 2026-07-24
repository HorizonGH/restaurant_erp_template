from typing import TypeVar

from sqlalchemy_filterset import (
    AsyncFilterSet,
    BooleanFilter,
    Filter,
    InFilter,
    IsNullFilter,
    LimitOffsetFilter,
    NotInFilter,
    NullsPosition,
    OrderingField,
    OrderingFilter,
    RangeFilter,
    SearchFilter,
)

from app.core.shared.domain.entities import BaseEntity

__all__ = [
    "AsyncFilterSet",
    "BaseFilterSet",
    "BooleanFilter",
    "Filter",
    "InFilter",
    "IsNullFilter",
    "LimitOffsetFilter",
    "NotInFilter",
    "NullsPosition",
    "OrderingField",
    "OrderingFilter",
    "RangeFilter",
    "SearchFilter",
]

EntityT = TypeVar("EntityT", bound=BaseEntity)


class BaseFilterSet(AsyncFilterSet[EntityT]):
    """Base FilterSet: every domain FilterSet gets limit/offset pagination for free.

    Subclasses add their own filters and an ``ordering = OrderingFilter(...)``.
    The dict passed to ``.filter()``/``.count()`` uses each attribute name as key,
    e.g. ``{"limit_offset": page_params.limit_offset, "ordering": ["-created_at"]}``.
    """

    limit_offset = LimitOffsetFilter()
