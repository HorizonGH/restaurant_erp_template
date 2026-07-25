from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.catalog.application.schemas import (
    CategoryCreateInput,
    CategoryOutput,
    CategoryUpdateInput,
)
from app.modules.catalog.application.service import CategoryService

router = APIRouter(prefix="/categories", tags=["Catalog - Categories"])


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> CategoryService:
    return CategoryService(session)


@router.get("/", response_model=APIResponse[Page[CategoryOutput]])
async def list_categories(
    params: Annotated[PageParams, Depends()],
    parent_id: UUID | None = Query(default=None),
    service: CategoryService = Depends(get_service),
) -> APIResponse[Page[CategoryOutput]]:
    filter_params: dict = {"limit_offset": params.limit_offset}
    if parent_id is not None:
        filter_params["parent_id"] = parent_id
    items, total = await service.list(filter_params)
    return APIResponse(data=Page.create(items, total, params))


@router.post("/", response_model=APIResponse[CategoryOutput], status_code=201)
async def create_category(
    data: CategoryCreateInput,
    service: CategoryService = Depends(get_service),
) -> APIResponse[CategoryOutput]:
    category = await service.create(data)
    return APIResponse(data=CategoryOutput.model_validate(category))


@router.get("/{category_id}", response_model=APIResponse[CategoryOutput])
async def get_category(
    category_id: UUID,
    service: CategoryService = Depends(get_service),
) -> APIResponse[CategoryOutput]:
    category = await service.get(category_id)
    return APIResponse(data=CategoryOutput.model_validate(category))


@router.patch("/{category_id}", response_model=APIResponse[CategoryOutput])
async def update_category(
    category_id: UUID,
    data: CategoryUpdateInput,
    service: CategoryService = Depends(get_service),
) -> APIResponse[CategoryOutput]:
    category = await service.update(category_id, data)
    return APIResponse(data=CategoryOutput.model_validate(category))


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: UUID,
    service: CategoryService = Depends(get_service),
) -> None:
    await service.delete(category_id)
