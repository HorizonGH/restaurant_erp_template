from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.inventory.application.schemas import (
    MovementAdjustmentInput,
    MovementEntryInput,
    MovementExitInput,
    StockMovementOutput,
)
from app.modules.inventory.application.service import MovementService, KardexService
from app.modules.inventory.infrastructure.repository import StockMovementRepository
from app.modules.inventory.infrastructure.filters import StockMovementFilterSet

router = APIRouter(prefix="/movements", tags=["Inventory - Movements"])


def get_movement_service(session=Depends(get_session)) -> MovementService:
    return MovementService(session)


def get_list_service(session=Depends(get_session)):
    return StockMovementRepository(session)


@router.post("/entry", response_model=APIResponse[StockMovementOutput], status_code=status.HTTP_201_CREATED)
async def record_entry(
    body: MovementEntryInput,
    service: MovementService = Depends(get_movement_service),
):
    movement = await service.record_entry(body)
    return APIResponse(data=StockMovementOutput.model_validate(movement))


@router.post("/exit", response_model=APIResponse[StockMovementOutput], status_code=status.HTTP_201_CREATED)
async def record_exit(
    body: MovementExitInput,
    service: MovementService = Depends(get_movement_service),
):
    movement = await service.record_exit(body)
    return APIResponse(data=StockMovementOutput.model_validate(movement))


@router.post("/adjustment", response_model=APIResponse[StockMovementOutput], status_code=status.HTTP_201_CREATED)
async def record_adjustment(
    body: MovementAdjustmentInput,
    service: MovementService = Depends(get_movement_service),
):
    movement = await service.record_adjustment(body)
    return APIResponse(data=StockMovementOutput.model_validate(movement))


@router.get("/", response_model=APIResponse[Page[StockMovementOutput]])
async def list_movements(
    params: Annotated[PageParams, Depends()],
    ingredient_id: str | None = Query(default=None),
    location_id: str | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    reference_type: str | None = Query(default=None),
    repo: StockMovementRepository = Depends(get_list_service),
):
    filters = {}
    if ingredient_id is not None:
        filters["ingredient_id"] = ingredient_id
    if location_id is not None:
        filters["location_id"] = location_id
    if movement_type is not None:
        filters["movement_type"] = movement_type
    if reference_type is not None:
        filters["reference_type"] = reference_type
    limit, offset = params.limit_offset
    filters["limit"] = limit
    filters["offset"] = offset
    items, total = await repo.list(StockMovementFilterSet, filters)
    return APIResponse(
        data=Page.create(
            items=[StockMovementOutput.model_validate(i) for i in items],
            total=total,
            params=params,
        )
    )
