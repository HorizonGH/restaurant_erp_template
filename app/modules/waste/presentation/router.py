from __future__ import annotations

from fastapi import APIRouter

from app.modules.waste.presentation.categories_router import router as categories_router
from app.modules.waste.presentation.records_router import router as records_router

router = APIRouter()
router.include_router(categories_router)
router.include_router(records_router)
