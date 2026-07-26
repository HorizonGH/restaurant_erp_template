from __future__ import annotations

from fastapi import APIRouter

from app.modules.purchasing.presentation.invoices_router import router as invoices_router
from app.modules.purchasing.presentation.po_router import router as po_router
from app.modules.purchasing.presentation.receipts_router import router as receipts_router

router = APIRouter()

router.include_router(po_router)
router.include_router(receipts_router)
router.include_router(invoices_router)
