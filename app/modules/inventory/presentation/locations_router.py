from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.inventory.application.schemas import (
    LocationCreateInput,
    LocationOutput,
    LocationSelectOutput,
    LocationUpdateInput,
)
from app.modules.inventory.application.service import LocationService

router = APIRouter(prefix="/locations", tags=["Inventory - Locations"])


def get_service(session=Depends(get_session)) -> LocationService:
    return LocationService(session)


@router.get("/select", response_model=APIResponse[list[LocationSelectOutput]])
async def select_locations(service: LocationService = Depends(get_service)):
    items = await service.select()
    return APIResponse(data=[LocationSelectOutput.model_validate(i) for i in items])


@router.get("/", response_model=APIResponse[Page[LocationOutput]])
async def list_locations(
    params: Annotated[PageParams, Depends()],
    location_type: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    service: LocationService = Depends(get_service),
):
    filters = {}
    if location_type is not None:
        filters["location_type"] = location_type
    if is_active is not None:
        filters["is_active"] = is_active
    limit, offset = params.limit_offset
    filters["limit"] = limit
    filters["offset"] = offset
    items, total = await service.list(filters)
    return APIResponse(
        data=Page.create(
            items=[LocationOutput.model_validate(i) for i in items],
            total=total,
            params=params,
        )
    )


@router.post("/", response_model=APIResponse[LocationOutput], status_code=status.HTTP_201_CREATED)
async def create_location(
    body: LocationCreateInput,
    service: LocationService = Depends(get_service),
):
    location = await service.create(body)
    return APIResponse(data=LocationOutput.model_validate(location))


@router.get("/{location_id}", response_model=APIResponse[LocationOutput])
async def get_location(
    location_id: UUID,
    service: LocationService = Depends(get_service),
):
    location = await service.get(location_id)
    return APIResponse(data=LocationOutput.model_validate(location))


@router.patch("/{location_id}", response_model=APIResponse[LocationOutput])
async def update_location(
    location_id: UUID,
    body: LocationUpdateInput,
    service: LocationService = Depends(get_service),
):
    location = await service.update(location_id, body)
    return APIResponse(data=LocationOutput.model_validate(location))


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: UUID,
    service: LocationService = Depends(get_service),
):
    await service.delete(location_id)


@router.patch("/{location_id}/activate", response_model=APIResponse[LocationOutput])
async def activate_location(
    location_id: UUID,
    service: LocationService = Depends(get_service),
):
    location = await service.set_active(location_id, is_active=True)
    return APIResponse(data=LocationOutput.model_validate(location))


@router.patch("/{location_id}/deactivate", response_model=APIResponse[LocationOutput])
async def deactivate_location(
    location_id: UUID,
    service: LocationService = Depends(get_service),
):
    location = await service.set_active(location_id, is_active=False)
    return APIResponse(data=LocationOutput.model_validate(location))
