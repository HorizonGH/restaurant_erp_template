from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.purchasing.application.schemas import (
    ReceiptCreateInput,
    ReceiptLineCreateInput,
    ReceiptLineOutput,
    ReceiptLineUpdateInput,
    ReceiptOutput,
    ReceiptUpdateInput,
)
from app.modules.purchasing.application.service import ReceivingService

router = APIRouter(prefix="/receipts", tags=["Purchasing - Receipts"])


@router.get("/", response_model=APIResponse[Page[ReceiptOutput]])
async def list_receipts(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    order_id: UUID | None = None,
    destination_location_id: UUID | None = None,
    status: str | None = None,
    ordering: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    svc = ReceivingService(session)
    params: dict = {k: v for k, v in {
        "page": page, "size": size,
        "order_id": order_id,
        "destination_location_id": destination_location_id,
        "status": status, "ordering": ordering,
    }.items() if v is not None}
    items, total = await svc.list(params)
    page_params = PageParams(page=page, size=size)
    return APIResponse(data=Page.create(items, total, page_params))


@router.post("/", response_model=APIResponse[ReceiptOutput], status_code=status.HTTP_201_CREATED)
async def create_receipt(
    body: ReceiptCreateInput,
    session: AsyncSession = Depends(get_session),
):
    svc = ReceivingService(session)
    receipt = await svc.create(body)
    return APIResponse(data=receipt)


@router.get("/{receipt_id}", response_model=APIResponse[ReceiptOutput])
async def get_receipt(receipt_id: UUID, session: AsyncSession = Depends(get_session)):
    svc = ReceivingService(session)
    receipt = await svc.get(receipt_id)
    return APIResponse(data=receipt)


@router.patch("/{receipt_id}", response_model=APIResponse[ReceiptOutput])
async def update_receipt(
    receipt_id: UUID,
    body: ReceiptUpdateInput,
    session: AsyncSession = Depends(get_session),
):
    svc = ReceivingService(session)
    receipt = await svc.update(receipt_id, body)
    return APIResponse(data=receipt)


@router.post("/{receipt_id}/complete", response_model=APIResponse[ReceiptOutput])
async def complete_receipt(receipt_id: UUID, session: AsyncSession = Depends(get_session)):
    svc = ReceivingService(session)
    receipt = await svc.complete(receipt_id)
    return APIResponse(data=receipt)


@router.post("/{receipt_id}/cancel", response_model=APIResponse[ReceiptOutput])
async def cancel_receipt(receipt_id: UUID, session: AsyncSession = Depends(get_session)):
    svc = ReceivingService(session)
    receipt = await svc.cancel(receipt_id)
    return APIResponse(data=receipt)


# ---------- Lines ----------

@router.get("/{receipt_id}/lines", response_model=APIResponse[list[ReceiptLineOutput]])
async def list_lines(receipt_id: UUID, session: AsyncSession = Depends(get_session)):
    svc = ReceivingService(session)
    lines = await svc.list_lines(receipt_id)
    return APIResponse(data=lines)


@router.post(
    "/{receipt_id}/lines",
    response_model=APIResponse[ReceiptLineOutput],
    status_code=status.HTTP_201_CREATED,
)
async def add_line(
    receipt_id: UUID,
    body: ReceiptLineCreateInput,
    session: AsyncSession = Depends(get_session),
):
    svc = ReceivingService(session)
    line = await svc.add_line(receipt_id, body)
    return APIResponse(data=line)


@router.patch("/{receipt_id}/lines/{line_id}", response_model=APIResponse[ReceiptLineOutput])
async def update_line(
    receipt_id: UUID,
    line_id: UUID,
    body: ReceiptLineUpdateInput,
    session: AsyncSession = Depends(get_session),
):
    svc = ReceivingService(session)
    line = await svc.update_line(receipt_id, line_id, body)
    return APIResponse(data=line)


@router.delete("/{receipt_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_line(
    receipt_id: UUID,
    line_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    svc = ReceivingService(session)
    await svc.remove_line(receipt_id, line_id)
