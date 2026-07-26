from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.waste.application.schemas import (
    WasteCategoryCreateInput,
    WasteCategoryOutput,
    WasteCategoryUpdateInput,
)
from app.modules.waste.application.service import WasteCategoryService

router = APIRouter(prefix="/categories", tags=["Waste - Categories"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WasteCategoryService:
    return WasteCategoryService(session)


@router.get("/select", response_model=APIResponse[list[WasteCategoryOutput]])
async def select_categories(
    service: WasteCategoryService = Depends(get_service),
) -> APIResponse[list[WasteCategoryOutput]]:
    items = await service.list_all()
    return APIResponse(data=[WasteCategoryOutput.model_validate(c) for c in items])


@router.get("/", response_model=APIResponse[Page[WasteCategoryOutput]])
async def list_categories(
    params: Annotated[PageParams, Depends()],
    name: str | None = Query(default=None),
    ordering: str | None = Query(default=None),
    service: WasteCategoryService = Depends(get_service),
) -> APIResponse[Page[WasteCategoryOutput]]:
    filter_params: dict = {"limit_offset": params.limit_offset}
    if name is not None:
        filter_params["name"] = f"%{name}%"
    if ordering is not None:
        filter_params["ordering"] = ordering
    items, total = await service.list(filter_params)
    return APIResponse(data=Page.create(items, total, params))


@router.post(
    "/",
    response_model=APIResponse[WasteCategoryOutput],
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    data: WasteCategoryCreateInput,
    service: WasteCategoryService = Depends(get_service),
) -> APIResponse[WasteCategoryOutput]:
    category = await service.create(data)
    return APIResponse(data=WasteCategoryOutput.model_validate(category))


@router.get("/{category_id}", response_model=APIResponse[WasteCategoryOutput])
async def get_category(
    category_id: UUID,
    service: WasteCategoryService = Depends(get_service),
) -> APIResponse[WasteCategoryOutput]:
    category = await service.get(category_id)
    return APIResponse(data=WasteCategoryOutput.model_validate(category))


@router.patch("/{category_id}", response_model=APIResponse[WasteCategoryOutput])
async def update_category(
    category_id: UUID,
    data: WasteCategoryUpdateInput,
    service: WasteCategoryService = Depends(get_service),
) -> APIResponse[WasteCategoryOutput]:
    category = await service.update(category_id, data)
    return APIResponse(data=WasteCategoryOutput.model_validate(category))


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    service: WasteCategoryService = Depends(get_service),
) -> None:
    await service.delete(category_id)
