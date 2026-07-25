from uuid import UUID

from sqlalchemy import func, select

from app.core.shared.infrastructure.repository import BaseRepository
from app.modules.catalog.domain.models import (
    Category,
    Ingredient,
    Supplier,
    SupplierIngredient,
    UnitOfMeasure,
)


class CategoryRepository(BaseRepository[Category]):
    model = Category

    async def has_children(self, category_id: UUID) -> bool:
        result = await self.session.execute(
            select(func.count()).where(Category.parent_id == category_id)
        )
        return result.scalar_one() > 0

    async def has_ingredients(self, category_id: UUID) -> bool:
        result = await self.session.execute(
            select(func.count()).where(Ingredient.category_id == category_id)
        )
        return result.scalar_one() > 0

    async def get_by_name(self, name: str) -> Category | None:
        result = await self.session.execute(
            select(Category).where(Category.name == name)
        )
        return result.scalar_one_or_none()


class UnitOfMeasureRepository(BaseRepository[UnitOfMeasure]):
    model = UnitOfMeasure

    async def get_by_abbreviation(self, abbreviation: str) -> UnitOfMeasure | None:
        result = await self.session.execute(
            select(UnitOfMeasure).where(UnitOfMeasure.abbreviation == abbreviation)
        )
        return result.scalar_one_or_none()


class IngredientRepository(BaseRepository[Ingredient]):
    model = Ingredient

    async def get_by_sku(self, sku: str) -> Ingredient | None:
        result = await self.session.execute(
            select(Ingredient).where(Ingredient.sku == sku)
        )
        return result.scalar_one_or_none()

    async def count_by_category(self, category_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count()).where(Ingredient.category_id == category_id)
        )
        return result.scalar_one()


class SupplierRepository(BaseRepository[Supplier]):
    model = Supplier


class SupplierIngredientRepository(BaseRepository[SupplierIngredient]):
    model = SupplierIngredient

    async def get_link(
        self, supplier_id: UUID, ingredient_id: UUID
    ) -> SupplierIngredient | None:
        result = await self.session.execute(
            select(SupplierIngredient).where(
                SupplierIngredient.supplier_id == supplier_id,
                SupplierIngredient.ingredient_id == ingredient_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_ingredient(self, ingredient_id: UUID) -> list[SupplierIngredient]:
        result = await self.session.execute(
            select(SupplierIngredient).where(
                SupplierIngredient.ingredient_id == ingredient_id
            )
        )
        return list(result.scalars().all())

    async def list_by_supplier(self, supplier_id: UUID) -> list[SupplierIngredient]:
        result = await self.session.execute(
            select(SupplierIngredient).where(
                SupplierIngredient.supplier_id == supplier_id
            )
        )
        return list(result.scalars().all())
