from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.purchasing.application.schemas import (
    InvoiceCreateInput,
    InvoiceOutput,
    InvoiceUpdateInput,
)
from app.modules.purchasing.application.service import InvoiceService

router = APIRouter(prefix="/invoices", tags=["Purchasing - Invoices"])


@router.get("/", response_model=APIResponse[Page[InvoiceOutput]])
async def list_invoices(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    order_id: UUID | None = None,
    status: str | None = None,
    ordering: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    svc = InvoiceService(session)
    params: dict = {k: v for k, v in {
        "page": page, "size": size,
        "order_id": order_id, "status": status, "ordering": ordering,
    }.items() if v is not None}
    items, total = await svc.list(params)
    page_params = PageParams(page=page, size=size)
    return APIResponse(data=Page.create(items, total, page_params))


@router.post("/", response_model=APIResponse[InvoiceOutput], status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: InvoiceCreateInput,
    session: AsyncSession = Depends(get_session),
):
    svc = InvoiceService(session)
    invoice = await svc.create(body)
    return APIResponse(data=invoice)


@router.get("/{invoice_id}", response_model=APIResponse[InvoiceOutput])
async def get_invoice(invoice_id: UUID, session: AsyncSession = Depends(get_session)):
    svc = InvoiceService(session)
    invoice = await svc.get(invoice_id)
    return APIResponse(data=invoice)


@router.patch("/{invoice_id}", response_model=APIResponse[InvoiceOutput])
async def update_invoice(
    invoice_id: UUID,
    body: InvoiceUpdateInput,
    session: AsyncSession = Depends(get_session),
):
    svc = InvoiceService(session)
    invoice = await svc.update(invoice_id, body)
    return APIResponse(data=invoice)


@router.post("/{invoice_id}/match", response_model=APIResponse[InvoiceOutput])
async def match_invoice(invoice_id: UUID, session: AsyncSession = Depends(get_session)):
    svc = InvoiceService(session)
    invoice = await svc.match(invoice_id)
    return APIResponse(data=invoice)


@router.post("/{invoice_id}/pay", response_model=APIResponse[InvoiceOutput])
async def pay_invoice(invoice_id: UUID, session: AsyncSession = Depends(get_session)):
    svc = InvoiceService(session)
    invoice = await svc.mark_paid(invoice_id)
    return APIResponse(data=invoice)


@router.post("/{invoice_id}/dispute", response_model=APIResponse[InvoiceOutput])
async def dispute_invoice(invoice_id: UUID, session: AsyncSession = Depends(get_session)):
    svc = InvoiceService(session)
    invoice = await svc.dispute(invoice_id)
    return APIResponse(data=invoice)
