from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.waste.application.schemas import (
    WasteRecordCreateInput,
    WasteRecordOutput,
    WasteSummaryLineOutput,
)
from app.modules.waste.application.service import WasteRecordService
from fastapi import status

router = APIRouter(prefix="/records", tags=["Waste - Records"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WasteRecordService:
    return WasteRecordService(session)


@router.get("/summary", response_model=APIResponse[list[WasteSummaryLineOutput]])
async def get_summary(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    location_id: UUID | None = Query(default=None),
    waste_category_id: UUID | None = Query(default=None),
    service: WasteRecordService = Depends(get_service),
) -> APIResponse[list[WasteSummaryLineOutput]]:
    summary = await service.get_summary(
        from_date=from_date,
        to_date=to_date,
        location_id=location_id,
        waste_category_id=waste_category_id,
    )
    return APIResponse(data=summary)


@router.get("/", response_model=APIResponse[Page[WasteRecordOutput]])
async def list_records(
    params: Annotated[PageParams, Depends()],
    ingredient_id: UUID | None = Query(default=None),
    location_id: UUID | None = Query(default=None),
    waste_category_id: UUID | None = Query(default=None),
    waste_date__gte: date | None = Query(default=None),
    waste_date__lte: date | None = Query(default=None),
    ordering: str | None = Query(default=None),
    service: WasteRecordService = Depends(get_service),
) -> APIResponse[Page[WasteRecordOutput]]:
    filter_params: dict = {"limit_offset": params.limit_offset}
    if ingredient_id is not None:
        filter_params["ingredient_id"] = ingredient_id
    if location_id is not None:
        filter_params["location_id"] = location_id
    if waste_category_id is not None:
        filter_params["waste_category_id"] = waste_category_id
    if waste_date__gte is not None:
        filter_params["waste_date__gte"] = waste_date__gte
    if waste_date__lte is not None:
        filter_params["waste_date__lte"] = waste_date__lte
    if ordering is not None:
        filter_params["ordering"] = ordering
    items, total = await service.list(filter_params)
    return APIResponse(data=Page.create(items, total, params))


@router.post(
    "/",
    response_model=APIResponse[WasteRecordOutput],
    status_code=status.HTTP_201_CREATED,
)
async def record_waste(
    data: WasteRecordCreateInput,
    service: WasteRecordService = Depends(get_service),
) -> APIResponse[WasteRecordOutput]:
    record = await service.record_waste(data)
    return APIResponse(data=WasteRecordOutput.model_validate(record))


@router.get("/{record_id}", response_model=APIResponse[WasteRecordOutput])
async def get_record(
    record_id: UUID,
    service: WasteRecordService = Depends(get_service),
) -> APIResponse[WasteRecordOutput]:
    record = await service.get(record_id)
    return APIResponse(data=WasteRecordOutput.model_validate(record))
