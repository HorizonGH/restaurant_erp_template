from sqlalchemy_filterset import OrderingField

from app.core.shared.infrastructure.filters import (
    BaseFilterSet,
    BooleanFilter,
    Filter,
    InFilter,
    NullsPosition,
    OrderingFilter,
    SearchFilter,
)
from app.modules.catalog.domain.models import Category, Ingredient, Supplier, UnitOfMeasure


class CategoryFilterSet(BaseFilterSet[Category]):
    parent_id = Filter(Category.parent_id)
    ordering = OrderingFilter(
        fields={
            "name": OrderingField(Category.name),
            "created_at": OrderingField(Category.created_at, nulls=NullsPosition.last),
        }
    )


class UnitOfMeasureFilterSet(BaseFilterSet[UnitOfMeasure]):
    unit_type = Filter(UnitOfMeasure.unit_type)
    ordering = OrderingFilter(
        fields={
            "name": OrderingField(UnitOfMeasure.name),
            "abbreviation": OrderingField(UnitOfMeasure.abbreviation),
        }
    )


class IngredientFilterSet(BaseFilterSet[Ingredient]):
    name = SearchFilter(Ingredient.name)
    sku = SearchFilter(Ingredient.sku)
    category_id = Filter(Ingredient.category_id)
    category_ids = InFilter(Ingredient.category_id)
    is_active = BooleanFilter(Ingredient.is_active)
    ordering = OrderingFilter(
        fields={
            "name": OrderingField(Ingredient.name),
            "sku": OrderingField(Ingredient.sku),
            "created_at": OrderingField(Ingredient.created_at, nulls=NullsPosition.last),
        }
    )


class SupplierFilterSet(BaseFilterSet[Supplier]):
    name = SearchFilter(Supplier.name)
    is_active = BooleanFilter(Supplier.is_active)
    ordering = OrderingFilter(
        fields={
            "name": OrderingField(Supplier.name),
            "created_at": OrderingField(Supplier.created_at, nulls=NullsPosition.last),
        }
    )
