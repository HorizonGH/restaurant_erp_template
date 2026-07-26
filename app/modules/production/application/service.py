from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.domain.exceptions import ConflictException, NotFoundException
from app.core.shared.domain.helpers import utcnow
from app.modules.catalog.infrastructure.repository import (
    IngredientRepository,
    UnitOfMeasureRepository,
)
from app.modules.inventory.application.schemas import MovementExitInput
from app.modules.inventory.application.service import MovementService
from app.modules.inventory.domain.enums import MovementType
from app.modules.inventory.infrastructure.repository import (
    LocationRepository,
    StockItemRepository,
)
from app.modules.production.application.schemas import (
    CompleteOrderInput,
    ProductionOrderCreateInput,
    ProductionOrderUpdateInput,
    RecipeCreateInput,
    RecipeIngredientCreateInput,
    RecipeIngredientUpdateInput,
    RecipeUpdateInput,
)
from app.modules.production.domain.enums import ProductionOrderStatus
from app.modules.production.domain.exceptions import (
    EmptyProductionOrderException,
    EmptyRecipeException,
    InsufficientStockForProductionException,
    OrderAlreadyCancelledException,
    OrderAlreadyCompletedException,
    OrderNotConfirmedException,
    OrderNotDraftException,
    OrderNotInProgressException,
    RecipeInUseException,
)
from app.modules.production.domain.models import (
    ProductionOrder,
    ProductionOrderLine,
    Recipe,
    RecipeIngredient,
    YieldRecord,
)
from app.modules.production.infrastructure.filters import (
    ProductionOrderFilterSet,
    RecipeFilterSet,
)
from app.modules.production.infrastructure.repository import (
    ProductionOrderLineRepository,
    ProductionOrderRepository,
    RecipeIngredientRepository,
    RecipeRepository,
    YieldRecordRepository,
)


def _generate_order_number() -> str:
    today = date.today()
    suffix = uuid.uuid4().hex[:5].upper()
    return f"PRD-{today.strftime('%Y%m')}-{suffix}"


# ---------------------------------------------------------------------------
# RecipeService
# ---------------------------------------------------------------------------

class RecipeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RecipeRepository(session)
        self.ingredient_repo = RecipeIngredientRepository(session)
        self.catalog_ingredient_repo = IngredientRepository(session)
        self.uom_repo = UnitOfMeasureRepository(session)

    async def get(self, recipe_id: UUID) -> Recipe:
        return await self.repo.get_or_404(recipe_id)

    async def select(self) -> list[Recipe]:
        return await self.repo.list_active()

    async def list(self, params: dict) -> tuple[Sequence[Recipe], int]:
        return await self.repo.list(RecipeFilterSet, params)

    async def create(self, data: RecipeCreateInput) -> Recipe:
        existing = await self.repo.get_by_name(data.name)
        if existing is not None:
            raise ConflictException(f"Recipe '{data.name}' already exists")
        await self.uom_repo.get_or_404(data.yield_unit_id)
        if data.output_ingredient_id is not None:
            await self.catalog_ingredient_repo.get_or_404(data.output_ingredient_id)
        recipe = await self.repo.create(**data.model_dump())
        await self.session.commit()
        return recipe

    async def update(self, recipe_id: UUID, data: RecipeUpdateInput) -> Recipe:
        recipe = await self.repo.get_or_404(recipe_id)
        values = data.model_dump(exclude_none=True)
        if "name" in values:
            existing = await self.repo.get_by_name(values["name"])
            if existing is not None and existing.entity_id != recipe_id:
                raise ConflictException(f"Recipe '{values['name']}' already exists")
        if "yield_unit_id" in values:
            await self.uom_repo.get_or_404(values["yield_unit_id"])
        if "output_ingredient_id" in values and values["output_ingredient_id"] is not None:
            await self.catalog_ingredient_repo.get_or_404(values["output_ingredient_id"])
        # Bump version on every update so production orders can detect stale recipes
        values["version"] = recipe.version + 1
        recipe = await self.repo.update(recipe, **values)
        await self.session.commit()
        return recipe

    async def delete(self, recipe_id: UUID) -> None:
        recipe = await self.repo.get_or_404(recipe_id)
        if await self.repo.has_production_orders(recipe_id):
            raise RecipeInUseException(
                "Cannot delete a recipe that has production orders"
            )
        await self.repo.soft_delete(recipe)
        await self.session.commit()

    async def set_active(self, recipe_id: UUID, *, is_active: bool) -> Recipe:
        recipe = await self.repo.get_or_404(recipe_id)
        recipe = await self.repo.update(recipe, is_active=is_active)
        await self.session.commit()
        return recipe

    # ------ Ingredient management ------

    async def list_ingredients(self, recipe_id: UUID) -> list[RecipeIngredient]:
        await self.repo.get_or_404(recipe_id)
        return await self.ingredient_repo.list_by_recipe(recipe_id)

    async def add_ingredient(
        self, recipe_id: UUID, data: RecipeIngredientCreateInput
    ) -> RecipeIngredient:
        recipe = await self.repo.get_or_404(recipe_id)
        await self.catalog_ingredient_repo.get_or_404(data.ingredient_id)
        await self.uom_repo.get_or_404(data.unit_of_measure_id)
        existing = await self.ingredient_repo.get_by_recipe_and_ingredient(
            recipe_id, data.ingredient_id
        )
        if existing is not None:
            raise ConflictException(
                "This ingredient already exists in the recipe"
            )
        line = await self.ingredient_repo.create(recipe_id=recipe_id, **data.model_dump())
        # Bump recipe version when ingredients change
        await self.repo.update(recipe, version=recipe.version + 1)
        await self.session.commit()
        return line

    async def update_ingredient(
        self,
        recipe_id: UUID,
        ingredient_line_id: UUID,
        data: RecipeIngredientUpdateInput,
    ) -> RecipeIngredient:
        recipe = await self.repo.get_or_404(recipe_id)
        line = await self.ingredient_repo.get_or_404(ingredient_line_id)
        if line.recipe_id != recipe_id:
            raise NotFoundException("Ingredient not found in this recipe")
        values = data.model_dump(exclude_none=True)
        if "unit_of_measure_id" in values:
            await self.uom_repo.get_or_404(values["unit_of_measure_id"])
        line = await self.ingredient_repo.update(line, **values)
        await self.repo.update(recipe, version=recipe.version + 1)
        await self.session.commit()
        return line

    async def remove_ingredient(
        self, recipe_id: UUID, ingredient_line_id: UUID
    ) -> None:
        recipe = await self.repo.get_or_404(recipe_id)
        line = await self.ingredient_repo.get_or_404(ingredient_line_id)
        if line.recipe_id != recipe_id:
            raise NotFoundException("Ingredient not found in this recipe")
        await self.ingredient_repo.soft_delete(line)
        await self.repo.update(recipe, version=recipe.version + 1)
        await self.session.commit()


# ---------------------------------------------------------------------------
# ProductionOrderService
# ---------------------------------------------------------------------------

class ProductionOrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ProductionOrderRepository(session)
        self.line_repo = ProductionOrderLineRepository(session)
        self.recipe_repo = RecipeRepository(session)
        self.recipe_ingredient_repo = RecipeIngredientRepository(session)
        self.location_repo = LocationRepository(session)
        self.stock_repo = StockItemRepository(session)
        self.yield_repo = YieldRecordRepository(session)
        self.movement_svc = MovementService(session)

    async def get(self, order_id: UUID) -> ProductionOrder:
        return await self.repo.get_or_404(order_id)

    async def list(self, params: dict) -> tuple[Sequence[ProductionOrder], int]:
        return await self.repo.list(ProductionOrderFilterSet, params)

    async def create(self, data: ProductionOrderCreateInput) -> ProductionOrder:
        recipe = await self.recipe_repo.get_or_404(data.recipe_id)
        if not recipe.is_active:
            raise RecipeInUseException("Cannot create a production order for an inactive recipe")
        await self.location_repo.get_or_404(data.source_location_id)

        recipe_lines = await self.recipe_ingredient_repo.list_by_recipe(data.recipe_id)
        if not recipe_lines:
            raise EmptyRecipeException(
                "Cannot create a production order from a recipe with no ingredients"
            )

        order_number = _generate_order_number()
        if await self.repo.get_by_number(order_number) is not None:
            order_number = _generate_order_number()

        order = await self.repo.create(
            order_number=order_number,
            recipe_id=data.recipe_id,
            source_location_id=data.source_location_id,
            status=ProductionOrderStatus.draft,
            quantity_to_produce=data.quantity_to_produce,
            scheduled_date=data.scheduled_date,
            notes=data.notes,
        )

        # Pre-populate order lines from recipe, snapshotting current availability
        for recipe_line in recipe_lines:
            required = recipe_line.quantity * data.quantity_to_produce
            stock = await self.stock_repo.get_by_ingredient_and_location(
                recipe_line.ingredient_id, data.source_location_id
            )
            available = stock.quantity_available if stock is not None else Decimal("0")
            await self.line_repo.create(
                order_id=order.entity_id,
                ingredient_id=recipe_line.ingredient_id,
                required_quantity=required,
                consumed_quantity=Decimal("0"),
                available_quantity=available,
            )

        await self.session.commit()
        return order

    async def update(
        self, order_id: UUID, data: ProductionOrderUpdateInput
    ) -> ProductionOrder:
        order = await self.repo.get_or_404(order_id)
        if order.status != ProductionOrderStatus.draft:
            raise OrderNotDraftException("Only draft orders can be updated")
        values = data.model_dump(exclude_none=True)

        # If quantity_to_produce changes, recalculate line required quantities
        if "quantity_to_produce" in values:
            recipe_lines = await self.recipe_ingredient_repo.list_by_recipe(order.recipe_id)
            order_lines = await self.line_repo.list_by_order(order_id)
            order_line_map = {l.ingredient_id: l for l in order_lines}
            new_qty = values["quantity_to_produce"]
            for recipe_line in recipe_lines:
                order_line = order_line_map.get(recipe_line.ingredient_id)
                if order_line is not None:
                    required = recipe_line.quantity * new_qty
                    stock = await self.stock_repo.get_by_ingredient_and_location(
                        recipe_line.ingredient_id, order.source_location_id
                    )
                    available = (
                        stock.quantity_available if stock is not None else Decimal("0")
                    )
                    await self.line_repo.update(
                        order_line,
                        required_quantity=required,
                        available_quantity=available,
                    )

        order = await self.repo.update(order, **values)
        await self.session.commit()
        return order

    async def confirm(self, order_id: UUID) -> ProductionOrder:
        """
        Transitions draft → confirmed.
        Refreshes stock availability snapshot and raises if any ingredient is short.
        """
        order = await self.repo.get_or_404(order_id)
        if order.status != ProductionOrderStatus.draft:
            raise OrderNotDraftException("Only draft orders can be confirmed")

        lines = await self.line_repo.list_by_order(order_id)
        if not lines:
            raise EmptyProductionOrderException("Production order has no lines")

        shortages: list[str] = []
        for line in lines:
            stock = await self.stock_repo.get_by_ingredient_and_location(
                line.ingredient_id, order.source_location_id
            )
            available = stock.quantity_available if stock is not None else Decimal("0")
            await self.line_repo.update(line, available_quantity=available)
            if available < line.required_quantity:
                shortages.append(
                    f"ingredient {line.ingredient_id}: "
                    f"required={line.required_quantity}, available={available}"
                )

        if shortages:
            raise InsufficientStockForProductionException(
                "Insufficient stock for production: " + "; ".join(shortages)
            )

        order = await self.repo.update(order, status=ProductionOrderStatus.confirmed)
        await self.session.commit()
        return order

    async def start(self, order_id: UUID) -> ProductionOrder:
        """
        Transitions confirmed → in_progress. Records started_at timestamp.
        """
        order = await self.repo.get_or_404(order_id)
        if order.status != ProductionOrderStatus.confirmed:
            raise OrderNotConfirmedException("Only confirmed orders can be started")
        order = await self.repo.update(
            order,
            status=ProductionOrderStatus.in_progress,
            started_at=utcnow(),
        )
        await self.session.commit()
        return order

    async def complete(
        self, order_id: UUID, data: CompleteOrderInput
    ) -> ProductionOrder:
        """
        Transitions in_progress → completed.

        For each order line:
          - Fires a production_consumption exit movement
          - Records consumed_quantity (= required_quantity; actual consumption)

        Creates a YieldRecord comparing expected vs actual yield.
        """
        order = await self.repo.get_or_404(order_id)
        if order.status == ProductionOrderStatus.completed:
            raise OrderAlreadyCompletedException("Order is already completed")
        if order.status != ProductionOrderStatus.in_progress:
            raise OrderNotInProgressException("Only in-progress orders can be completed")

        lines = await self.line_repo.list_by_order(order_id)
        if not lines:
            raise EmptyProductionOrderException("Production order has no lines")

        recipe = await self.recipe_repo.get_or_404(order.recipe_id)

        for line in lines:
            await self.movement_svc.record_exit(
                MovementExitInput(
                    ingredient_id=line.ingredient_id,
                    location_id=order.source_location_id,
                    quantity=line.required_quantity,
                    reference_type="production_order",
                    reference_id=order.entity_id,
                    notes=f"Production order {order.order_number} — recipe {recipe.name}",
                ),
                movement_type=MovementType.production_consumption,
            )
            await self.line_repo.update(
                line, consumed_quantity=line.required_quantity
            )

        # Yield record
        expected_yield = recipe.yield_quantity * order.quantity_to_produce
        await self.yield_repo.create(
            order_id=order_id,
            expected_yield=expected_yield,
            actual_yield=data.actual_yield,
            notes=data.notes,
        )

        order = await self.repo.update(
            order,
            status=ProductionOrderStatus.completed,
            completed_at=utcnow(),
        )
        await self.session.commit()
        return order

    async def cancel(self, order_id: UUID) -> ProductionOrder:
        order = await self.repo.get_or_404(order_id)
        if order.status == ProductionOrderStatus.cancelled:
            raise OrderAlreadyCancelledException("Order is already cancelled")
        if order.status == ProductionOrderStatus.completed:
            raise OrderAlreadyCompletedException("Completed orders cannot be cancelled")
        order = await self.repo.update(order, status=ProductionOrderStatus.cancelled)
        await self.session.commit()
        return order

    async def check_availability(self, order_id: UUID) -> ProductionOrder:
        """
        Refreshes the available_quantity snapshot on every order line without
        changing the order status. Returns the updated order.
        """
        order = await self.repo.get_or_404(order_id)
        lines = await self.line_repo.list_by_order(order_id)
        for line in lines:
            stock = await self.stock_repo.get_by_ingredient_and_location(
                line.ingredient_id, order.source_location_id
            )
            available = stock.quantity_available if stock is not None else Decimal("0")
            await self.line_repo.update(line, available_quantity=available)
        await self.session.commit()
        return order

    async def list_lines(self, order_id: UUID) -> list[ProductionOrderLine]:
        await self.repo.get_or_404(order_id)
        return await self.line_repo.list_by_order(order_id)

    async def get_yield(self, order_id: UUID) -> YieldRecord:
        await self.repo.get_or_404(order_id)
        record = await self.yield_repo.get_by_order(order_id)
        if record is None:
            raise NotFoundException("No yield record found for this order")
        return record
