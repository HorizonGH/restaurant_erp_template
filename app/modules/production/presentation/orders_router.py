from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.production.application.schemas import (
    CompleteOrderInput,
    OrderAvailabilityOutput,
    ProductionOrderCreateInput,
    ProductionOrderLineOutput,
    ProductionOrderOutput,
    ProductionOrderUpdateInput,
    IngredientAvailabilityOutput,
    YieldRecordOutput,
)
from app.modules.production.application.service import ProductionOrderService

router = APIRouter(prefix="/orders", tags=["Production - Orders"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProductionOrderService:
    return ProductionOrderService(session)


@router.get("/", response_model=APIResponse[Page[ProductionOrderOutput]])
async def list_orders(
    params: Annotated[PageParams, Depends()],
    recipe_id: UUID | None = Query(default=None),
    source_location_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    ordering: str | None = Query(default=None),
    service: ProductionOrderService = Depends(get_service),
) -> APIResponse[Page[ProductionOrderOutput]]:
    filter_params: dict = {"limit_offset": params.limit_offset}
    if recipe_id is not None:
        filter_params["recipe_id"] = recipe_id
    if source_location_id is not None:
        filter_params["source_location_id"] = source_location_id
    if status is not None:
        filter_params["status"] = status
    if ordering is not None:
        filter_params["ordering"] = ordering
    items, total = await service.list(filter_params)
    return APIResponse(data=Page.create(items, total, params))


@router.post("/", response_model=APIResponse[ProductionOrderOutput], status_code=status.HTTP_201_CREATED)
async def create_order(
    data: ProductionOrderCreateInput,
    service: ProductionOrderService = Depends(get_service),
) -> APIResponse[ProductionOrderOutput]:
    order = await service.create(data)
    return APIResponse(data=ProductionOrderOutput.model_validate(order))


@router.get("/{order_id}", response_model=APIResponse[ProductionOrderOutput])
async def get_order(
    order_id: UUID,
    service: ProductionOrderService = Depends(get_service),
) -> APIResponse[ProductionOrderOutput]:
    order = await service.get(order_id)
    return APIResponse(data=ProductionOrderOutput.model_validate(order))


@router.patch("/{order_id}", response_model=APIResponse[ProductionOrderOutput])
async def update_order(
    order_id: UUID,
    data: ProductionOrderUpdateInput,
    service: ProductionOrderService = Depends(get_service),
) -> APIResponse[ProductionOrderOutput]:
    order = await service.update(order_id, data)
    return APIResponse(data=ProductionOrderOutput.model_validate(order))


@router.post("/{order_id}/confirm", response_model=APIResponse[ProductionOrderOutput])
async def confirm_order(
    order_id: UUID,
    service: ProductionOrderService = Depends(get_service),
) -> APIResponse[ProductionOrderOutput]:
    order = await service.confirm(order_id)
    return APIResponse(data=ProductionOrderOutput.model_validate(order))


@router.post("/{order_id}/start", response_model=APIResponse[ProductionOrderOutput])
async def start_order(
    order_id: UUID,
    service: ProductionOrderService = Depends(get_service),
) -> APIResponse[ProductionOrderOutput]:
    order = await service.start(order_id)
    return APIResponse(data=ProductionOrderOutput.model_validate(order))


@router.post("/{order_id}/complete", response_model=APIResponse[ProductionOrderOutput])
async def complete_order(
    order_id: UUID,
    data: CompleteOrderInput,
    service: ProductionOrderService = Depends(get_service),
) -> APIResponse[ProductionOrderOutput]:
    order = await service.complete(order_id, data)
    return APIResponse(data=ProductionOrderOutput.model_validate(order))


@router.post("/{order_id}/cancel", response_model=APIResponse[ProductionOrderOutput])
async def cancel_order(
    order_id: UUID,
    service: ProductionOrderService = Depends(get_service),
) -> APIResponse[ProductionOrderOutput]:
    order = await service.cancel(order_id)
    return APIResponse(data=ProductionOrderOutput.model_validate(order))


@router.get("/{order_id}/availability", response_model=APIResponse[OrderAvailabilityOutput])
async def check_availability(
    order_id: UUID,
    service: ProductionOrderService = Depends(get_service),
) -> APIResponse[OrderAvailabilityOutput]:
    order = await service.check_availability(order_id)
    lines = await service.list_lines(order_id)
    availability_lines = [
        IngredientAvailabilityOutput(
            ingredient_id=l.ingredient_id,
            required_quantity=l.required_quantity,
            available_quantity=l.available_quantity,
            is_available=l.is_available,
            shortage=l.shortage,
        )
        for l in lines
    ]
    all_available = all(l.is_available for l in lines)
    return APIResponse(
        data=OrderAvailabilityOutput(
            order_id=order.entity_id,
            all_available=all_available,
            lines=availability_lines,
        )
    )


@router.get("/{order_id}/lines", response_model=APIResponse[list[ProductionOrderLineOutput]])
async def list_order_lines(
    order_id: UUID,
    service: ProductionOrderService = Depends(get_service),
) -> APIResponse[list[ProductionOrderLineOutput]]:
    lines = await service.list_lines(order_id)
    return APIResponse(data=[ProductionOrderLineOutput.model_validate(l) for l in lines])


@router.get("/{order_id}/yield", response_model=APIResponse[YieldRecordOutput])
async def get_yield(
    order_id: UUID,
    service: ProductionOrderService = Depends(get_service),
) -> APIResponse[YieldRecordOutput]:
    record = await service.get_yield(order_id)
    return APIResponse(data=YieldRecordOutput.model_validate(record))
