from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.transfers.application.schemas import (
    PhysicalCountCreateInput,
    PhysicalCountLineOutput,
    PhysicalCountLineRecordInput,
    PhysicalCountOutput,
    PhysicalCountUpdateInput,
)
from app.modules.transfers.application.service import PhysicalCountService

router = APIRouter(prefix="/counts", tags=["Physical Counts"])


def get_service(session=Depends(get_session)) -> PhysicalCountService:
    return PhysicalCountService(session)


@router.get("/", response_model=APIResponse[Page[PhysicalCountOutput]])
async def list_counts(
    params: Annotated[PageParams, Depends()],
    location_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    service: PhysicalCountService = Depends(get_service),
):
    filters: dict = {}
    if location_id is not None:
        filters["location_id"] = location_id
    if status is not None:
        filters["status"] = status
    limit, offset = params.limit_offset
    filters["limit"] = limit
    filters["offset"] = offset
    items, total = await service.list(filters)
    return APIResponse(
        data=Page.create(
            items=[PhysicalCountOutput.model_validate(i) for i in items],
            total=total,
            params=params,
        )
    )


@router.post("/", response_model=APIResponse[PhysicalCountOutput], status_code=status.HTTP_201_CREATED)
async def create_count(
    body: PhysicalCountCreateInput,
    service: PhysicalCountService = Depends(get_service),
):
    count = await service.create(body)
    return APIResponse(data=PhysicalCountOutput.model_validate(count))


@router.get("/{count_id}", response_model=APIResponse[PhysicalCountOutput])
async def get_count(
    count_id: UUID,
    service: PhysicalCountService = Depends(get_service),
):
    count = await service.get(count_id)
    return APIResponse(data=PhysicalCountOutput.model_validate(count))


@router.patch("/{count_id}", response_model=APIResponse[PhysicalCountOutput])
async def update_count(
    count_id: UUID,
    body: PhysicalCountUpdateInput,
    service: PhysicalCountService = Depends(get_service),
):
    count = await service.update(count_id, body)
    return APIResponse(data=PhysicalCountOutput.model_validate(count))


# --- Lifecycle ---

@router.post("/{count_id}/complete", response_model=APIResponse[PhysicalCountOutput])
async def complete_count(
    count_id: UUID,
    service: PhysicalCountService = Depends(get_service),
):
    count = await service.complete(count_id)
    return APIResponse(data=PhysicalCountOutput.model_validate(count))


@router.post("/{count_id}/cancel", response_model=APIResponse[PhysicalCountOutput])
async def cancel_count(
    count_id: UUID,
    service: PhysicalCountService = Depends(get_service),
):
    count = await service.cancel(count_id)
    return APIResponse(data=PhysicalCountOutput.model_validate(count))


# --- Lines ---

@router.get("/{count_id}/lines", response_model=APIResponse[list[PhysicalCountLineOutput]])
async def list_count_lines(
    count_id: UUID,
    service: PhysicalCountService = Depends(get_service),
):
    lines = await service.list_lines(count_id)
    return APIResponse(data=[PhysicalCountLineOutput.model_validate(l) for l in lines])


@router.patch(
    "/{count_id}/lines/{line_id}",
    response_model=APIResponse[PhysicalCountLineOutput],
)
async def record_count_line(
    count_id: UUID,
    line_id: UUID,
    body: PhysicalCountLineRecordInput,
    service: PhysicalCountService = Depends(get_service),
):
    line = await service.record_line(count_id, line_id, body)
    return APIResponse(data=PhysicalCountLineOutput.model_validate(line))
