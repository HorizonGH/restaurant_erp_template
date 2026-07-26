from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.sales.application.schemas import (
    SalesOrderCreateInput,
    SalesOrderLineCreateInput,
    SalesOrderLineOutput,
    SalesOrderLineUpdateInput,
    SalesOrderOutput,
    SalesOrderUpdateInput,
)
from app.modules.sales.application.service import SalesOrderService

router = APIRouter(prefix="/orders", tags=["Sales - Orders"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SalesOrderService:
    return SalesOrderService(session)


@router.get("/", response_model=APIResponse[Page[SalesOrderOutput]])
async def list_orders(
    params: Annotated[PageParams, Depends()],
    source_location_id: UUID | None = Query(default=None),
    channel: str | None = Query(default=None),
    status: str | None = Query(default=None),
    ordering: str | None = Query(default=None),
    service: SalesOrderService = Depends(get_service),
) -> APIResponse[Page[SalesOrderOutput]]:
    filter_params: dict = {"limit_offset": params.limit_offset}
    if source_location_id is not None:
        filter_params["source_location_id"] = source_location_id
    if channel is not None:
        filter_params["channel"] = channel
    if status is not None:
        filter_params["status"] = status
    if ordering is not None:
        filter_params["ordering"] = ordering
    items, total = await service.list(filter_params)
    return APIResponse(data=Page.create(items, total, params))


@router.post("/", response_model=APIResponse[SalesOrderOutput], status_code=status.HTTP_201_CREATED)
async def create_order(
    data: SalesOrderCreateInput,
    service: SalesOrderService = Depends(get_service),
) -> APIResponse[SalesOrderOutput]:
    order = await service.create(data)
    return APIResponse(data=SalesOrderOutput.model_validate(order))


@router.get("/{order_id}", response_model=APIResponse[SalesOrderOutput])
async def get_order(
    order_id: UUID,
    service: SalesOrderService = Depends(get_service),
) -> APIResponse[SalesOrderOutput]:
    order = await service.get(order_id)
    return APIResponse(data=SalesOrderOutput.model_validate(order))


@router.patch("/{order_id}", response_model=APIResponse[SalesOrderOutput])
async def update_order(
    order_id: UUID,
    data: SalesOrderUpdateInput,
    service: SalesOrderService = Depends(get_service),
) -> APIResponse[SalesOrderOutput]:
    order = await service.update(order_id, data)
    return APIResponse(data=SalesOrderOutput.model_validate(order))


@router.post("/{order_id}/confirm", response_model=APIResponse[SalesOrderOutput])
async def confirm_order(
    order_id: UUID,
    service: SalesOrderService = Depends(get_service),
) -> APIResponse[SalesOrderOutput]:
    order = await service.confirm(order_id)
    return APIResponse(data=SalesOrderOutput.model_validate(order))


@router.post("/{order_id}/prepare", response_model=APIResponse[SalesOrderOutput])
async def start_preparation(
    order_id: UUID,
    service: SalesOrderService = Depends(get_service),
) -> APIResponse[SalesOrderOutput]:
    order = await service.start_preparation(order_id)
    return APIResponse(data=SalesOrderOutput.model_validate(order))


@router.post("/{order_id}/ready", response_model=APIResponse[SalesOrderOutput])
async def mark_ready(
    order_id: UUID,
    service: SalesOrderService = Depends(get_service),
) -> APIResponse[SalesOrderOutput]:
    order = await service.mark_ready(order_id)
    return APIResponse(data=SalesOrderOutput.model_validate(order))


@router.post("/{order_id}/deliver", response_model=APIResponse[SalesOrderOutput])
async def deliver_order(
    order_id: UUID,
    service: SalesOrderService = Depends(get_service),
) -> APIResponse[SalesOrderOutput]:
    order = await service.deliver(order_id)
    return APIResponse(data=SalesOrderOutput.model_validate(order))


@router.post("/{order_id}/cancel", response_model=APIResponse[SalesOrderOutput])
async def cancel_order(
    order_id: UUID,
    service: SalesOrderService = Depends(get_service),
) -> APIResponse[SalesOrderOutput]:
    order = await service.cancel(order_id)
    return APIResponse(data=SalesOrderOutput.model_validate(order))


# ---------- Lines ----------

@router.get("/{order_id}/lines", response_model=APIResponse[list[SalesOrderLineOutput]])
async def list_lines(
    order_id: UUID,
    service: SalesOrderService = Depends(get_service),
) -> APIResponse[list[SalesOrderLineOutput]]:
    lines = await service.list_lines(order_id)
    return APIResponse(data=[SalesOrderLineOutput.model_validate(l) for l in lines])


@router.post(
    "/{order_id}/lines",
    response_model=APIResponse[SalesOrderLineOutput],
    status_code=status.HTTP_201_CREATED,
)
async def add_line(
    order_id: UUID,
    data: SalesOrderLineCreateInput,
    service: SalesOrderService = Depends(get_service),
) -> APIResponse[SalesOrderLineOutput]:
    line = await service.add_line(order_id, data)
    return APIResponse(data=SalesOrderLineOutput.model_validate(line))


@router.patch(
    "/{order_id}/lines/{line_id}",
    response_model=APIResponse[SalesOrderLineOutput],
)
async def update_line(
    order_id: UUID,
    line_id: UUID,
    data: SalesOrderLineUpdateInput,
    service: SalesOrderService = Depends(get_service),
) -> APIResponse[SalesOrderLineOutput]:
    line = await service.update_line(order_id, line_id, data)
    return APIResponse(data=SalesOrderLineOutput.model_validate(line))


@router.delete("/{order_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_line(
    order_id: UUID,
    line_id: UUID,
    service: SalesOrderService = Depends(get_service),
) -> None:
    await service.remove_line(order_id, line_id)
