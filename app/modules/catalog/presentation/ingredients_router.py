from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.catalog.application.schemas import (
    IngredientCreateInput,
    IngredientDetailOutput,
    IngredientOutput,
    IngredientUpdateInput,
    SupplierIngredientLinkInput,
    SupplierIngredientOutput,
)
from app.modules.catalog.application.service import IngredientService, SupplierIngredientService

router = APIRouter(prefix="/ingredients", tags=["Catalog - Ingredients"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IngredientService:
    return IngredientService(session)


def get_link_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupplierIngredientService:
    return SupplierIngredientService(session)


@router.get("/", response_model=APIResponse[Page[IngredientOutput]])
async def list_ingredients(
    params: Annotated[PageParams, Query()],
    name: str | None = Query(default=None),
    sku: str | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    service: IngredientService = Depends(get_service),
) -> APIResponse[Page[IngredientOutput]]:
    filter_params: dict = {"limit_offset": params.limit_offset}
    if name is not None:
        filter_params["name"] = f"%{name}%"
    if sku is not None:
        filter_params["sku"] = f"%{sku}%"
    if category_id is not None:
        filter_params["category_id"] = category_id
    if is_active is not None:
        filter_params["is_active"] = is_active
    items, total = await service.list(filter_params)
    return APIResponse(data=Page.create(items, total, params))


@router.post("/", response_model=APIResponse[IngredientOutput], status_code=201)
async def create_ingredient(
    data: IngredientCreateInput,
    service: IngredientService = Depends(get_service),
) -> APIResponse[IngredientOutput]:
    ingredient = await service.create(data)
    return APIResponse(data=IngredientOutput.model_validate(ingredient))


@router.get("/{ingredient_id}", response_model=APIResponse[IngredientDetailOutput])
async def get_ingredient(
    ingredient_id: UUID,
    service: IngredientService = Depends(get_service),
) -> APIResponse[IngredientDetailOutput]:
    ingredient = await service.get(ingredient_id)
    return APIResponse(data=IngredientDetailOutput.model_validate(ingredient))


@router.patch("/{ingredient_id}", response_model=APIResponse[IngredientOutput])
async def update_ingredient(
    ingredient_id: UUID,
    data: IngredientUpdateInput,
    service: IngredientService = Depends(get_service),
) -> APIResponse[IngredientOutput]:
    ingredient = await service.update(ingredient_id, data)
    return APIResponse(data=IngredientOutput.model_validate(ingredient))


@router.delete("/{ingredient_id}", status_code=204)
async def delete_ingredient(
    ingredient_id: UUID,
    service: IngredientService = Depends(get_service),
) -> None:
    await service.delete(ingredient_id)


@router.get(
    "/{ingredient_id}/suppliers",
    response_model=APIResponse[list[SupplierIngredientOutput]],
)
async def list_ingredient_suppliers(
    ingredient_id: UUID,
    service: SupplierIngredientService = Depends(get_link_service),
) -> APIResponse[list[SupplierIngredientOutput]]:
    links = await service.list_by_ingredient(ingredient_id)
    return APIResponse(data=[SupplierIngredientOutput.model_validate(l) for l in links])


@router.post(
    "/{ingredient_id}/suppliers/{supplier_id}",
    response_model=APIResponse[SupplierIngredientOutput],
    status_code=201,
)
async def link_supplier_to_ingredient(
    ingredient_id: UUID,
    supplier_id: UUID,
    data: SupplierIngredientLinkInput,
    service: SupplierIngredientService = Depends(get_link_service),
) -> APIResponse[SupplierIngredientOutput]:
    link = await service.link(supplier_id, ingredient_id, data)
    return APIResponse(data=SupplierIngredientOutput.model_validate(link))
