from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.core.shared.infrastructure.repository import BaseRepository
from app.modules.production.domain.models import (
    ProductionOrder,
    ProductionOrderLine,
    Recipe,
    RecipeIngredient,
    YieldRecord,
)


class RecipeRepository(BaseRepository[Recipe]):
    model = Recipe

    async def get_by_name(self, name: str) -> Recipe | None:
        result = await self.session.execute(
            select(Recipe).where(
                Recipe.name == name,
                Recipe.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Recipe]:
        result = await self.session.execute(
            select(Recipe).where(
                Recipe.is_deleted.is_(False),
                Recipe.is_active.is_(True),
            ).order_by(Recipe.name)
        )
        return list(result.scalars().all())

    async def has_production_orders(self, recipe_id: UUID) -> bool:
        result = await self.session.execute(
            select(ProductionOrder).where(
                ProductionOrder.recipe_id == recipe_id,
                ProductionOrder.is_deleted.is_(False),
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None


class RecipeIngredientRepository(BaseRepository[RecipeIngredient]):
    model = RecipeIngredient

    async def list_by_recipe(self, recipe_id: UUID) -> list[RecipeIngredient]:
        result = await self.session.execute(
            select(RecipeIngredient).where(
                RecipeIngredient.recipe_id == recipe_id,
                RecipeIngredient.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())

    async def get_by_recipe_and_ingredient(
        self, recipe_id: UUID, ingredient_id: UUID
    ) -> RecipeIngredient | None:
        result = await self.session.execute(
            select(RecipeIngredient).where(
                RecipeIngredient.recipe_id == recipe_id,
                RecipeIngredient.ingredient_id == ingredient_id,
                RecipeIngredient.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()


class ProductionOrderRepository(BaseRepository[ProductionOrder]):
    model = ProductionOrder

    async def get_by_number(self, order_number: str) -> ProductionOrder | None:
        result = await self.session.execute(
            select(ProductionOrder).where(
                ProductionOrder.order_number == order_number,
                ProductionOrder.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()


class ProductionOrderLineRepository(BaseRepository[ProductionOrderLine]):
    model = ProductionOrderLine

    async def list_by_order(self, order_id: UUID) -> list[ProductionOrderLine]:
        result = await self.session.execute(
            select(ProductionOrderLine).where(
                ProductionOrderLine.order_id == order_id,
                ProductionOrderLine.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())

    async def get_by_order_and_ingredient(
        self, order_id: UUID, ingredient_id: UUID
    ) -> ProductionOrderLine | None:
        result = await self.session.execute(
            select(ProductionOrderLine).where(
                ProductionOrderLine.order_id == order_id,
                ProductionOrderLine.ingredient_id == ingredient_id,
                ProductionOrderLine.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()


class YieldRecordRepository(BaseRepository[YieldRecord]):
    model = YieldRecord

    async def get_by_order(self, order_id: UUID) -> YieldRecord | None:
        result = await self.session.execute(
            select(YieldRecord).where(
                YieldRecord.order_id == order_id,
                YieldRecord.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()
