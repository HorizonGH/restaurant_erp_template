from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.domain.exceptions import ConflictException, NotFoundException
from app.modules.catalog.application.schemas import (
    CategoryCreateInput,
    CategoryUpdateInput,
    IngredientCreateInput,
    IngredientUpdateInput,
    SupplierCreateInput,
    SupplierIngredientLinkInput,
    SupplierUpdateInput,
    UnitOfMeasureCreateInput,
    UnitOfMeasureUpdateInput,
)
from app.modules.catalog.domain.exceptions import CategoryInUseException, DuplicateSKUException
from app.modules.catalog.domain.models import (
    Category,
    Ingredient,
    Supplier,
    SupplierIngredient,
    UnitOfMeasure,
)
from app.modules.catalog.infrastructure.filters import (
    CategoryFilterSet,
    IngredientFilterSet,
    SupplierFilterSet,
    UnitOfMeasureFilterSet,
)
from app.modules.catalog.infrastructure.repository import (
    CategoryRepository,
    IngredientRepository,
    SupplierIngredientRepository,
    SupplierRepository,
    UnitOfMeasureRepository,
)


class CategoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CategoryRepository(session)

    async def get(self, category_id: UUID) -> Category:
        return await self.repo.get_or_404(category_id)

    async def list(self, params: dict) -> tuple[Sequence[Category], int]:
        return await self.repo.list(CategoryFilterSet, params)

    async def create(self, data: CategoryCreateInput) -> Category:
        existing = await self.repo.get_by_name(data.name)
        if existing is not None:
            raise ConflictException(f"Category '{data.name}' already exists")
        if data.parent_id is not None:
            await self.repo.get_or_404(data.parent_id)
        category = await self.repo.create(**data.model_dump())
        await self.session.commit()
        return category

    async def update(self, category_id: UUID, data: CategoryUpdateInput) -> Category:
        category = await self.repo.get_or_404(category_id)
        values = data.model_dump(exclude_none=True)
        if "name" in values:
            existing = await self.repo.get_by_name(values["name"])
            if existing is not None and existing.entity_id != category_id:
                raise ConflictException(f"Category '{values['name']}' already exists")
        if "parent_id" in values and values["parent_id"] is not None:
            await self.repo.get_or_404(values["parent_id"])
        category = await self.repo.update(category, **values)
        await self.session.commit()
        return category

    async def delete(self, category_id: UUID) -> None:
        category = await self.repo.get_or_404(category_id)
        if await self.repo.has_children(category_id):
            raise CategoryInUseException("Cannot delete category with sub-categories")
        if await self.repo.has_ingredients(category_id):
            raise CategoryInUseException("Cannot delete category with ingredients")
        await self.repo.delete(category)
        await self.session.commit()


class UnitOfMeasureService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UnitOfMeasureRepository(session)

    async def get(self, unit_id: UUID) -> UnitOfMeasure:
        return await self.repo.get_or_404(unit_id)

    async def list(self, params: dict) -> tuple[Sequence[UnitOfMeasure], int]:
        return await self.repo.list(UnitOfMeasureFilterSet, params)

    async def create(self, data: UnitOfMeasureCreateInput) -> UnitOfMeasure:
        existing = await self.repo.get_by_abbreviation(data.abbreviation)
        if existing is not None:
            raise ConflictException(
                f"Unit with abbreviation '{data.abbreviation}' already exists"
            )
        if data.base_unit_id is not None:
            await self.repo.get_or_404(data.base_unit_id)
        unit = await self.repo.create(**data.model_dump())
        await self.session.commit()
        return unit

    async def update(self, unit_id: UUID, data: UnitOfMeasureUpdateInput) -> UnitOfMeasure:
        unit = await self.repo.get_or_404(unit_id)
        values = data.model_dump(exclude_none=True)
        if "abbreviation" in values:
            existing = await self.repo.get_by_abbreviation(values["abbreviation"])
            if existing is not None and existing.entity_id != unit_id:
                raise ConflictException(
                    f"Unit with abbreviation '{values['abbreviation']}' already exists"
                )
        if "base_unit_id" in values and values["base_unit_id"] is not None:
            await self.repo.get_or_404(values["base_unit_id"])
        unit = await self.repo.update(unit, **values)
        await self.session.commit()
        return unit

    async def delete(self, unit_id: UUID) -> None:
        unit = await self.repo.get_or_404(unit_id)
        await self.repo.delete(unit)
        await self.session.commit()


class IngredientService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = IngredientRepository(session)
        self.category_repo = CategoryRepository(session)
        self.uom_repo = UnitOfMeasureRepository(session)

    async def get(self, ingredient_id: UUID) -> Ingredient:
        return await self.repo.get_or_404(ingredient_id)

    async def list(self, params: dict) -> tuple[Sequence[Ingredient], int]:
        return await self.repo.list(IngredientFilterSet, params)

    async def create(self, data: IngredientCreateInput) -> Ingredient:
        existing = await self.repo.get_by_sku(data.sku)
        if existing is not None:
            raise DuplicateSKUException(f"SKU '{data.sku}' already exists")
        await self.category_repo.get_or_404(data.category_id)
        await self.uom_repo.get_or_404(data.unit_of_measure_id)
        ingredient = await self.repo.create(**data.model_dump())
        await self.session.commit()
        return ingredient

    async def update(self, ingredient_id: UUID, data: IngredientUpdateInput) -> Ingredient:
        ingredient = await self.repo.get_or_404(ingredient_id)
        values = data.model_dump(exclude_none=True)
        if "category_id" in values:
            await self.category_repo.get_or_404(values["category_id"])
        if "unit_of_measure_id" in values:
            await self.uom_repo.get_or_404(values["unit_of_measure_id"])
        ingredient = await self.repo.update(ingredient, **values)
        await self.session.commit()
        return ingredient

    async def delete(self, ingredient_id: UUID) -> None:
        ingredient = await self.repo.get_or_404(ingredient_id)
        await self.repo.delete(ingredient)
        await self.session.commit()


class SupplierService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SupplierRepository(session)

    async def get(self, supplier_id: UUID) -> Supplier:
        return await self.repo.get_or_404(supplier_id)

    async def list(self, params: dict) -> tuple[Sequence[Supplier], int]:
        return await self.repo.list(SupplierFilterSet, params)

    async def create(self, data: SupplierCreateInput) -> Supplier:
        supplier = await self.repo.create(**data.model_dump())
        await self.session.commit()
        return supplier

    async def update(self, supplier_id: UUID, data: SupplierUpdateInput) -> Supplier:
        supplier = await self.repo.get_or_404(supplier_id)
        values = data.model_dump(exclude_none=True)
        supplier = await self.repo.update(supplier, **values)
        await self.session.commit()
        return supplier

    async def delete(self, supplier_id: UUID) -> None:
        supplier = await self.repo.get_or_404(supplier_id)
        await self.repo.delete(supplier)
        await self.session.commit()


class SupplierIngredientService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SupplierIngredientRepository(session)
        self.supplier_repo = SupplierRepository(session)
        self.ingredient_repo = IngredientRepository(session)

    async def link(
        self,
        supplier_id: UUID,
        ingredient_id: UUID,
        data: SupplierIngredientLinkInput,
    ) -> SupplierIngredient:
        await self.supplier_repo.get_or_404(supplier_id)
        await self.ingredient_repo.get_or_404(ingredient_id)
        existing = await self.repo.get_link(supplier_id, ingredient_id)
        if existing is not None:
            link = await self.repo.update(existing, **data.model_dump(exclude_none=True))
        else:
            link = await self.repo.create(
                supplier_id=supplier_id,
                ingredient_id=ingredient_id,
                **data.model_dump(),
            )
        await self.session.commit()
        return link

    async def list_by_ingredient(self, ingredient_id: UUID) -> list[SupplierIngredient]:
        await self.ingredient_repo.get_or_404(ingredient_id)
        return await self.repo.list_by_ingredient(ingredient_id)

    async def list_by_supplier(self, supplier_id: UUID) -> list[SupplierIngredient]:
        await self.supplier_repo.get_or_404(supplier_id)
        return await self.repo.list_by_supplier(supplier_id)

    async def unlink(self, supplier_id: UUID, ingredient_id: UUID) -> None:
        link = await self.repo.get_link(supplier_id, ingredient_id)
        if link is None:
            raise NotFoundException("Supplier-ingredient link not found")
        await self.repo.delete(link)
        await self.session.commit()
