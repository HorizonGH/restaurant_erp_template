from fastapi import APIRouter

from app.modules.catalog.presentation.categories_router import router as categories_router
from app.modules.catalog.presentation.ingredients_router import router as ingredients_router
from app.modules.catalog.presentation.suppliers_router import router as suppliers_router
from app.modules.catalog.presentation.units_router import router as units_router

router = APIRouter()

router.include_router(categories_router)
router.include_router(units_router)
router.include_router(ingredients_router)
router.include_router(suppliers_router)
