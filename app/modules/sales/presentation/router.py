from __future__ import annotations

from fastapi import APIRouter

from app.modules.sales.presentation.orders_router import router as orders_router

router = APIRouter()
router.include_router(orders_router)
