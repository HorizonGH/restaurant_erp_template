from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.catalog.application.schemas import (
    SupplierCreateInput,
    SupplierIngredientLinkInput,
    SupplierIngredientOutput,
    SupplierOutput,
    SupplierUpdateInput,
)
from app.modules.catalog.application.service import SupplierIngredientService, SupplierService

router = APIRouter(prefix="/suppliers", tags=["Catalog - Suppliers"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupplierService:
    return SupplierService(session)


def get_link_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupplierIngredientService:
    return SupplierIngredientService(session)


@router.get("/", response_model=APIResponse[Page[SupplierOutput]])
async def list_suppliers(
    params: Annotated[PageParams, Depends()],
    name: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    service: SupplierService = Depends(get_service),
) -> APIResponse[Page[SupplierOutput]]:
    filter_params: dict = {"limit_offset": params.limit_offset}
    if name is not None:
        filter_params["name"] = f"%{name}%"
    if is_active is not None:
        filter_params["is_active"] = is_active
    items, total = await service.list(filter_params)
    return APIResponse(data=Page.create(items, total, params))


@router.post("/", response_model=APIResponse[SupplierOutput], status_code=201)
async def create_supplier(
    data: SupplierCreateInput,
    service: SupplierService = Depends(get_service),
) -> APIResponse[SupplierOutput]:
    supplier = await service.create(data)
    return APIResponse(data=SupplierOutput.model_validate(supplier))


@router.get("/{supplier_id}", response_model=APIResponse[SupplierOutput])
async def get_supplier(
    supplier_id: UUID,
    service: SupplierService = Depends(get_service),
) -> APIResponse[SupplierOutput]:
    supplier = await service.get(supplier_id)
    return APIResponse(data=SupplierOutput.model_validate(supplier))


@router.patch("/{supplier_id}", response_model=APIResponse[SupplierOutput])
async def update_supplier(
    supplier_id: UUID,
    data: SupplierUpdateInput,
    service: SupplierService = Depends(get_service),
) -> APIResponse[SupplierOutput]:
    supplier = await service.update(supplier_id, data)
    return APIResponse(data=SupplierOutput.model_validate(supplier))


@router.delete("/{supplier_id}", status_code=204)
async def delete_supplier(
    supplier_id: UUID,
    service: SupplierService = Depends(get_service),
) -> None:
    await service.delete(supplier_id)


@router.get(
    "/{supplier_id}/ingredients",
    response_model=APIResponse[list[SupplierIngredientOutput]],
)
async def list_supplier_ingredients(
    supplier_id: UUID,
    service: SupplierIngredientService = Depends(get_link_service),
) -> APIResponse[list[SupplierIngredientOutput]]:
    links = await service.list_by_supplier(supplier_id)
    return APIResponse(data=[SupplierIngredientOutput.model_validate(l) for l in links])


@router.post(
    "/{supplier_id}/ingredients/{ingredient_id}",
    response_model=APIResponse[SupplierIngredientOutput],
    status_code=201,
)
async def link_ingredient_to_supplier(
    supplier_id: UUID,
    ingredient_id: UUID,
    data: SupplierIngredientLinkInput,
    service: SupplierIngredientService = Depends(get_link_service),
) -> APIResponse[SupplierIngredientOutput]:
    link = await service.link(supplier_id, ingredient_id, data)
    return APIResponse(data=SupplierIngredientOutput.model_validate(link))


@router.delete("/{supplier_id}/ingredients/{ingredient_id}", status_code=204)
async def unlink_ingredient_from_supplier(
    supplier_id: UUID,
    ingredient_id: UUID,
    service: SupplierIngredientService = Depends(get_link_service),
) -> None:
    await service.unlink(supplier_id, ingredient_id)
