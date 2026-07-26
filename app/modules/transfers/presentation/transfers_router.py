from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.shared.infrastructure.database import get_session
from app.core.shared.presentation.pagination import Page, PageParams
from app.core.shared.presentation.responses import APIResponse
from app.modules.transfers.application.schemas import (
    TransferCreateInput,
    TransferLineCreateInput,
    TransferLineOutput,
    TransferLineUpdateInput,
    TransferOutput,
    TransferUpdateInput,
)
from app.modules.transfers.application.service import TransferService

router = APIRouter(prefix="/transfers", tags=["Transfers"])


def get_service(session=Depends(get_session)) -> TransferService:
    return TransferService(session)


@router.get("/", response_model=APIResponse[Page[TransferOutput]])
async def list_transfers(
    params: Annotated[PageParams, Depends()],
    from_location_id: UUID | None = Query(default=None),
    to_location_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    service: TransferService = Depends(get_service),
):
    filters: dict = {}
    if from_location_id is not None:
        filters["from_location_id"] = from_location_id
    if to_location_id is not None:
        filters["to_location_id"] = to_location_id
    if status is not None:
        filters["status"] = status
    limit, offset = params.limit_offset
    filters["limit"] = limit
    filters["offset"] = offset
    items, total = await service.list(filters)
    return APIResponse(
        data=Page.create(
            items=[TransferOutput.model_validate(i) for i in items],
            total=total,
            params=params,
        )
    )


@router.post("/", response_model=APIResponse[TransferOutput], status_code=status.HTTP_201_CREATED)
async def create_transfer(
    body: TransferCreateInput,
    service: TransferService = Depends(get_service),
):
    transfer = await service.create(body)
    return APIResponse(data=TransferOutput.model_validate(transfer))


@router.get("/{transfer_id}", response_model=APIResponse[TransferOutput])
async def get_transfer(
    transfer_id: UUID,
    service: TransferService = Depends(get_service),
):
    transfer = await service.get(transfer_id)
    return APIResponse(data=TransferOutput.model_validate(transfer))


@router.patch("/{transfer_id}", response_model=APIResponse[TransferOutput])
async def update_transfer(
    transfer_id: UUID,
    body: TransferUpdateInput,
    service: TransferService = Depends(get_service),
):
    transfer = await service.update(transfer_id, body)
    return APIResponse(data=TransferOutput.model_validate(transfer))


# --- Lifecycle ---

@router.post("/{transfer_id}/send", response_model=APIResponse[TransferOutput])
async def send_transfer(
    transfer_id: UUID,
    service: TransferService = Depends(get_service),
):
    transfer = await service.send(transfer_id)
    return APIResponse(data=TransferOutput.model_validate(transfer))


@router.post("/{transfer_id}/receive", response_model=APIResponse[TransferOutput])
async def receive_transfer(
    transfer_id: UUID,
    service: TransferService = Depends(get_service),
):
    transfer = await service.receive(transfer_id)
    return APIResponse(data=TransferOutput.model_validate(transfer))


@router.post("/{transfer_id}/cancel", response_model=APIResponse[TransferOutput])
async def cancel_transfer(
    transfer_id: UUID,
    service: TransferService = Depends(get_service),
):
    transfer = await service.cancel(transfer_id)
    return APIResponse(data=TransferOutput.model_validate(transfer))


# --- Lines ---

@router.get("/{transfer_id}/lines", response_model=APIResponse[list[TransferLineOutput]])
async def list_transfer_lines(
    transfer_id: UUID,
    service: TransferService = Depends(get_service),
):
    lines = await service.list_lines(transfer_id)
    return APIResponse(data=[TransferLineOutput.model_validate(l) for l in lines])


@router.post(
    "/{transfer_id}/lines",
    response_model=APIResponse[TransferLineOutput],
    status_code=status.HTTP_201_CREATED,
)
async def add_transfer_line(
    transfer_id: UUID,
    body: TransferLineCreateInput,
    service: TransferService = Depends(get_service),
):
    line = await service.add_line(transfer_id, body)
    return APIResponse(data=TransferLineOutput.model_validate(line))


@router.patch("/{transfer_id}/lines/{line_id}", response_model=APIResponse[TransferLineOutput])
async def update_transfer_line(
    transfer_id: UUID,
    line_id: UUID,
    body: TransferLineUpdateInput,
    service: TransferService = Depends(get_service),
):
    line = await service.update_line(transfer_id, line_id, body)
    return APIResponse(data=TransferLineOutput.model_validate(line))


@router.delete("/{transfer_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_transfer_line(
    transfer_id: UUID,
    line_id: UUID,
    service: TransferService = Depends(get_service),
):
    await service.remove_line(transfer_id, line_id)
