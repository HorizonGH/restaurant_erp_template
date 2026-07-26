from __future__ import annotations

from sqlalchemy_filterset import BooleanFilter, OrderingField, SearchFilter

from app.core.shared.infrastructure.filters import (
    BaseFilterSet,
    Filter,
    NullsPosition,
    OrderingFilter,
)
from app.modules.production.domain.models import (
    ProductionOrder,
    ProductionOrderLine,
    Recipe,
    RecipeIngredient,
)


class RecipeFilterSet(BaseFilterSet[Recipe]):
    name = SearchFilter(Recipe.name)
    is_active = BooleanFilter(Recipe.is_active)
    ordering = OrderingFilter(
        fields={
            "name": OrderingField(Recipe.name, nulls=NullsPosition.last),
            "created_at": OrderingField(Recipe.created_at, nulls=NullsPosition.last),
        }
    )


class RecipeIngredientFilterSet(BaseFilterSet[RecipeIngredient]):
    recipe_id = Filter(RecipeIngredient.recipe_id)
    ingredient_id = Filter(RecipeIngredient.ingredient_id)
    ordering = OrderingFilter(
        fields={
            "created_at": OrderingField(RecipeIngredient.created_at, nulls=NullsPosition.last),
        }
    )


class ProductionOrderFilterSet(BaseFilterSet[ProductionOrder]):
    recipe_id = Filter(ProductionOrder.recipe_id)
    status = Filter(ProductionOrder.status)
    source_location_id = Filter(ProductionOrder.source_location_id)
    ordering = OrderingFilter(
        fields={
            "scheduled_date": OrderingField(
                ProductionOrder.scheduled_date, nulls=NullsPosition.last
            ),
            "created_at": OrderingField(
                ProductionOrder.created_at, nulls=NullsPosition.last
            ),
        }
    )


class ProductionOrderLineFilterSet(BaseFilterSet[ProductionOrderLine]):
    order_id = Filter(ProductionOrderLine.order_id)
    ingredient_id = Filter(ProductionOrderLine.ingredient_id)
    ordering = OrderingFilter(
        fields={
            "created_at": OrderingField(
                ProductionOrderLine.created_at, nulls=NullsPosition.last
            ),
        }
    )
