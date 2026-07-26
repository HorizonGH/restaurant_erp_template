from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.purchasing.application.schemas import (
    POCreateInput,
    POLineCreateInput,
    POLineOutput,
    POLineUpdateInput,
    POOutput,
    POUpdateInput,
)
from app.modules.purchasing.application.service import PurchaseOrderService

router = APIRouter(prefix="/orders", tags=["Purchasing - Orders"])


@router.get("/", response_model=APIResponse[Page[POOutput]])
async def list_orders(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    supplier_id: UUID | None = None,
    status: str | None = None,
    ordering: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    svc = PurchaseOrderService(session)
    params: dict = {k: v for k, v in {
        "page": page, "size": size,
        "supplier_id": supplier_id, "status": status, "ordering": ordering,
    }.items() if v is not None}
    items, total = await svc.list(params)
    page_params = PageParams(page=page, size=size)
    return APIResponse(data=Page.create(items, total, page_params))


@router.post("/", response_model=APIResponse[POOutput], status_code=status.HTTP_201_CREATED)
async def create_order(
    body: POCreateInput,
    session: AsyncSession = Depends(get_session),
):
    svc = PurchaseOrderService(session)
    order = await svc.create(body)
    return APIResponse(data=order)


@router.get("/{order_id}", response_model=APIResponse[POOutput])
async def get_order(order_id: UUID, session: AsyncSession = Depends(get_session)):
    svc = PurchaseOrderService(session)
    order = await svc.get(order_id)
    return APIResponse(data=order)


@router.patch("/{order_id}", response_model=APIResponse[POOutput])
async def update_order(
    order_id: UUID,
    body: POUpdateInput,
    session: AsyncSession = Depends(get_session),
):
    svc = PurchaseOrderService(session)
    order = await svc.update(order_id, body)
    return APIResponse(data=order)


@router.post("/{order_id}/send", response_model=APIResponse[POOutput])
async def send_order(order_id: UUID, session: AsyncSession = Depends(get_session)):
    svc = PurchaseOrderService(session)
    order = await svc.send(order_id)
    return APIResponse(data=order)


@router.post("/{order_id}/cancel", response_model=APIResponse[POOutput])
async def cancel_order(order_id: UUID, session: AsyncSession = Depends(get_session)):
    svc = PurchaseOrderService(session)
    order = await svc.cancel(order_id)
    return APIResponse(data=order)


# ---------- Lines ----------

@router.get("/{order_id}/lines", response_model=APIResponse[list[POLineOutput]])
async def list_lines(order_id: UUID, session: AsyncSession = Depends(get_session)):
    svc = PurchaseOrderService(session)
    lines = await svc.list_lines(order_id)
    return APIResponse(data=lines)


@router.post(
    "/{order_id}/lines",
    response_model=APIResponse[POLineOutput],
    status_code=status.HTTP_201_CREATED,
)
async def add_line(
    order_id: UUID,
    body: POLineCreateInput,
    session: AsyncSession = Depends(get_session),
):
    svc = PurchaseOrderService(session)
    line = await svc.add_line(order_id, body)
    return APIResponse(data=line)


@router.patch("/{order_id}/lines/{line_id}", response_model=APIResponse[POLineOutput])
async def update_line(
    order_id: UUID,
    line_id: UUID,
    body: POLineUpdateInput,
    session: AsyncSession = Depends(get_session),
):
    svc = PurchaseOrderService(session)
    line = await svc.update_line(order_id, line_id, body)
    return APIResponse(data=line)


@router.delete(
    "/{order_id}/lines/{line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_line(
    order_id: UUID,
    line_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    svc = PurchaseOrderService(session)
    await svc.remove_line(order_id, line_id)
