from fastapi import APIRouter

from app.modules.inventory.presentation.batches_router import router as batches_router
from app.modules.inventory.presentation.kardex_router import router as kardex_router
from app.modules.inventory.presentation.locations_router import router as locations_router
from app.modules.inventory.presentation.movements_router import router as movements_router
from app.modules.inventory.presentation.stock_router import router as stock_router

router = APIRouter()

router.include_router(locations_router)
router.include_router(stock_router)
router.include_router(movements_router)
router.include_router(batches_router)
router.include_router(kardex_router)
