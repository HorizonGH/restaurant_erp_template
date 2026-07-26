from __future__ import annotations

from fastapi import APIRouter

from app.modules.production.presentation.orders_router import router as orders_router
from app.modules.production.presentation.recipes_router import router as recipes_router

router = APIRouter()

router.include_router(recipes_router)
router.include_router(orders_router)
