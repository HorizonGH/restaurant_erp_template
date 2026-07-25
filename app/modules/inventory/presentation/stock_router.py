from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.inventory.application.schemas import StockItemOutput
from app.modules.inventory.application.service import StockService

router = APIRouter(prefix="/stock", tags=["Inventory - Stock"])


def get_service(session=Depends(get_session)) -> StockService:
    return StockService(session)


@router.get("/", response_model=APIResponse[Page[StockItemOutput]])
async def list_stock(
    params: Annotated[PageParams, Depends()],
    ingredient_id: UUID | None = Query(default=None),
    location_id: UUID | None = Query(default=None),
    service: StockService = Depends(get_service),
):
    filters = {}
    if ingredient_id is not None:
        filters["ingredient_id"] = ingredient_id
    if location_id is not None:
        filters["location_id"] = location_id
    limit, offset = params.limit_offset
    filters["limit"] = limit
    filters["offset"] = offset
    items, total = await service.list_stock(filters)
    return APIResponse(
        data=Page.create(
            items=[StockItemOutput.model_validate(i) for i in items],
            total=total,
            params=params,
        )
    )


@router.get("/low-stock", response_model=APIResponse[list[StockItemOutput]])
async def list_low_stock(service: StockService = Depends(get_service)):
    items = await service.list_low_stock()
    return APIResponse(data=[StockItemOutput.model_validate(i) for i in items])


@router.get("/{ingredient_id}/locations", response_model=APIResponse[list[StockItemOutput]])
async def list_stock_by_ingredient(
    ingredient_id: UUID,
    service: StockService = Depends(get_service),
):
    items = await service.list_by_ingredient(ingredient_id)
    return APIResponse(data=[StockItemOutput.model_validate(i) for i in items])
