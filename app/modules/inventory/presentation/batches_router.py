from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.inventory.application.schemas import BatchOutput
from app.modules.inventory.application.service import BatchService

router = APIRouter(prefix="/batches", tags=["Inventory - Batches"])


def get_service(session=Depends(get_session)) -> BatchService:
    return BatchService(session)


@router.get("/expiring-soon", response_model=APIResponse[list[BatchOutput]])
async def list_expiring_soon(
    days: int = Query(default=7, ge=1, le=365),
    service: BatchService = Depends(get_service),
):
    items = await service.list_expiring_soon(days=days)
    return APIResponse(data=[BatchOutput.model_validate(i) for i in items])


@router.get("/", response_model=APIResponse[Page[BatchOutput]])
async def list_batches(
    params: Annotated[PageParams, Depends()],
    ingredient_id: UUID | None = Query(default=None),
    location_id: UUID | None = Query(default=None),
    supplier_id: UUID | None = Query(default=None),
    service: BatchService = Depends(get_service),
):
    filters = {}
    if ingredient_id is not None:
        filters["ingredient_id"] = ingredient_id
    if location_id is not None:
        filters["location_id"] = location_id
    if supplier_id is not None:
        filters["supplier_id"] = supplier_id
    limit, offset = params.limit_offset
    filters["limit"] = limit
    filters["offset"] = offset
    items, total = await service.list(filters)
    return APIResponse(
        data=Page.create(
            items=[BatchOutput.model_validate(i) for i in items],
            total=total,
            params=params,
        )
    )


@router.get("/{batch_id}", response_model=APIResponse[BatchOutput])
async def get_batch(
    batch_id: UUID,
    service: BatchService = Depends(get_service),
):
    batch = await service.get(batch_id)
    return APIResponse(data=BatchOutput.model_validate(batch))
