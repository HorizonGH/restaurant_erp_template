from fastapi import APIRouter

from app.modules.transfers.presentation.physical_counts_router import router as counts_router
from app.modules.transfers.presentation.transfers_router import router as transfers_router

router = APIRouter()

router.include_router(transfers_router)
router.include_router(counts_router)
