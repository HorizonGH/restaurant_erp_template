from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.catalog.application.schemas import (
    UnitOfMeasureCreateInput,
    UnitOfMeasureOutput,
    UnitOfMeasureUpdateInput,
)
from app.modules.catalog.application.service import UnitOfMeasureService
from app.modules.catalog.domain.enums import UnitType

router = APIRouter(prefix="/units", tags=["Catalog - Units of Measure"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UnitOfMeasureService:
    return UnitOfMeasureService(session)


@router.get("/", response_model=APIResponse[Page[UnitOfMeasureOutput]])
async def list_units(
    params: Annotated[PageParams, Depends()],
    unit_type: UnitType | None = Query(default=None),
    service: UnitOfMeasureService = Depends(get_service),
) -> APIResponse[Page[UnitOfMeasureOutput]]:
    filter_params: dict = {"limit_offset": params.limit_offset}
    if unit_type is not None:
        filter_params["unit_type"] = unit_type
    items, total = await service.list(filter_params)
    return APIResponse(data=Page.create(items, total, params))


@router.post("/", response_model=APIResponse[UnitOfMeasureOutput], status_code=201)
async def create_unit(
    data: UnitOfMeasureCreateInput,
    service: UnitOfMeasureService = Depends(get_service),
) -> APIResponse[UnitOfMeasureOutput]:
    unit = await service.create(data)
    return APIResponse(data=UnitOfMeasureOutput.model_validate(unit))


@router.get("/{unit_id}", response_model=APIResponse[UnitOfMeasureOutput])
async def get_unit(
    unit_id: UUID,
    service: UnitOfMeasureService = Depends(get_service),
) -> APIResponse[UnitOfMeasureOutput]:
    unit = await service.get(unit_id)
    return APIResponse(data=UnitOfMeasureOutput.model_validate(unit))


@router.patch("/{unit_id}", response_model=APIResponse[UnitOfMeasureOutput])
async def update_unit(
    unit_id: UUID,
    data: UnitOfMeasureUpdateInput,
    service: UnitOfMeasureService = Depends(get_service),
) -> APIResponse[UnitOfMeasureOutput]:
    unit = await service.update(unit_id, data)
    return APIResponse(data=UnitOfMeasureOutput.model_validate(unit))


@router.delete("/{unit_id}", status_code=204)
async def delete_unit(
    unit_id: UUID,
    service: UnitOfMeasureService = Depends(get_service),
) -> None:
    await service.delete(unit_id)
