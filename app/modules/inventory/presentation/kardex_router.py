from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.inventory.application.schemas import KardexEntryOutput
from app.modules.inventory.application.service import KardexService

router = APIRouter(prefix="/kardex", tags=["Inventory - Kardex"])


def get_service(session=Depends(get_session)) -> KardexService:
    return KardexService(session)


@router.get("/", response_model=APIResponse[Page[KardexEntryOutput]])
async def list_kardex(
    params: Annotated[PageParams, Depends()],
    ingredient_id: UUID | None = Query(default=None),
    location_id: UUID | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    service: KardexService = Depends(get_service),
):
    filters = {}
    if ingredient_id is not None:
        filters["ingredient_id"] = ingredient_id
    if location_id is not None:
        filters["location_id"] = location_id
    if movement_type is not None:
        filters["movement_type"] = movement_type
    limit, offset = params.limit_offset
    filters["limit"] = limit
    filters["offset"] = offset
    items, total = await service.list_kardex(filters)
    return APIResponse(
        data=Page.create(
            items=[KardexEntryOutput.model_validate(i) for i in items],
            total=total,
            params=params,
        )
    )


@router.get("/ingredient/{ingredient_id}", response_model=APIResponse[Page[KardexEntryOutput]])
async def list_kardex_by_ingredient(
    ingredient_id: UUID,
    params: Annotated[PageParams, Depends()],
    location_id: UUID | None = Query(default=None),
    service: KardexService = Depends(get_service),
):
    filters: dict = {"ingredient_id": ingredient_id}
    if location_id is not None:
        filters["location_id"] = location_id
    limit, offset = params.limit_offset
    filters["limit"] = limit
    filters["offset"] = offset
    items, total = await service.list_kardex(filters)
    return APIResponse(
        data=Page.create(
            items=[KardexEntryOutput.model_validate(i) for i in items],
            total=total,
            params=params,
        )
    )
