from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.production.application.schemas import (
    RecipeCreateInput,
    RecipeIngredientCreateInput,
    RecipeIngredientOutput,
    RecipeIngredientUpdateInput,
    RecipeOutput,
    RecipeUpdateInput,
)
from app.modules.production.application.service import RecipeService

router = APIRouter(prefix="/recipes", tags=["Production - Recipes"])


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> RecipeService:
    return RecipeService(session)


@router.get("/select", response_model=APIResponse[list[RecipeOutput]])
async def select_recipes(
    service: RecipeService = Depends(get_service),
) -> APIResponse[list[RecipeOutput]]:
    items = await service.select()
    return APIResponse(data=[RecipeOutput.model_validate(r) for r in items])


@router.get("/", response_model=APIResponse[Page[RecipeOutput]])
async def list_recipes(
    params: Annotated[PageParams, Query()],
    name: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    ordering: str | None = Query(default=None),
    service: RecipeService = Depends(get_service),
) -> APIResponse[Page[RecipeOutput]]:
    filter_params: dict = {"limit_offset": params.limit_offset}
    if name is not None:
        filter_params["name"] = f"%{name}%"
    if is_active is not None:
        filter_params["is_active"] = is_active
    if ordering is not None:
        filter_params["ordering"] = ordering
    items, total = await service.list(filter_params)
    return APIResponse(data=Page.create(items, total, params))


@router.post("/", response_model=APIResponse[RecipeOutput], status_code=status.HTTP_201_CREATED)
async def create_recipe(
    data: RecipeCreateInput,
    service: RecipeService = Depends(get_service),
) -> APIResponse[RecipeOutput]:
    recipe = await service.create(data)
    return APIResponse(data=RecipeOutput.model_validate(recipe))


@router.get("/{recipe_id}", response_model=APIResponse[RecipeOutput])
async def get_recipe(
    recipe_id: UUID,
    service: RecipeService = Depends(get_service),
) -> APIResponse[RecipeOutput]:
    recipe = await service.get(recipe_id)
    return APIResponse(data=RecipeOutput.model_validate(recipe))


@router.patch("/{recipe_id}", response_model=APIResponse[RecipeOutput])
async def update_recipe(
    recipe_id: UUID,
    data: RecipeUpdateInput,
    service: RecipeService = Depends(get_service),
) -> APIResponse[RecipeOutput]:
    recipe = await service.update(recipe_id, data)
    return APIResponse(data=RecipeOutput.model_validate(recipe))


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(
    recipe_id: UUID,
    service: RecipeService = Depends(get_service),
) -> None:
    await service.delete(recipe_id)


@router.patch("/{recipe_id}/activate", response_model=APIResponse[RecipeOutput])
async def activate_recipe(
    recipe_id: UUID,
    service: RecipeService = Depends(get_service),
) -> APIResponse[RecipeOutput]:
    recipe = await service.set_active(recipe_id, is_active=True)
    return APIResponse(data=RecipeOutput.model_validate(recipe))


@router.patch("/{recipe_id}/deactivate", response_model=APIResponse[RecipeOutput])
async def deactivate_recipe(
    recipe_id: UUID,
    service: RecipeService = Depends(get_service),
) -> APIResponse[RecipeOutput]:
    recipe = await service.set_active(recipe_id, is_active=False)
    return APIResponse(data=RecipeOutput.model_validate(recipe))


# ---------- Recipe Ingredients ----------

@router.get(
    "/{recipe_id}/ingredients",
    response_model=APIResponse[list[RecipeIngredientOutput]],
)
async def list_recipe_ingredients(
    recipe_id: UUID,
    service: RecipeService = Depends(get_service),
) -> APIResponse[list[RecipeIngredientOutput]]:
    lines = await service.list_ingredients(recipe_id)
    return APIResponse(data=[RecipeIngredientOutput.model_validate(l) for l in lines])


@router.post(
    "/{recipe_id}/ingredients",
    response_model=APIResponse[RecipeIngredientOutput],
    status_code=status.HTTP_201_CREATED,
)
async def add_recipe_ingredient(
    recipe_id: UUID,
    data: RecipeIngredientCreateInput,
    service: RecipeService = Depends(get_service),
) -> APIResponse[RecipeIngredientOutput]:
    line = await service.add_ingredient(recipe_id, data)
    return APIResponse(data=RecipeIngredientOutput.model_validate(line))


@router.patch(
    "/{recipe_id}/ingredients/{ingredient_line_id}",
    response_model=APIResponse[RecipeIngredientOutput],
)
async def update_recipe_ingredient(
    recipe_id: UUID,
    ingredient_line_id: UUID,
    data: RecipeIngredientUpdateInput,
    service: RecipeService = Depends(get_service),
) -> APIResponse[RecipeIngredientOutput]:
    line = await service.update_ingredient(recipe_id, ingredient_line_id, data)
    return APIResponse(data=RecipeIngredientOutput.model_validate(line))


@router.delete(
    "/{recipe_id}/ingredients/{ingredient_line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_recipe_ingredient(
    recipe_id: UUID,
    ingredient_line_id: UUID,
    service: RecipeService = Depends(get_service),
) -> None:
    await service.remove_ingredient(recipe_id, ingredient_line_id)
