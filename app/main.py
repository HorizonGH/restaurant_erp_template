from fastapi import FastAPI

from app.core.logging import configure_logging
from app.core.settings import settings
from app.core.shared.presentation.exception_handlers import register_exception_handlers
from app.middlewares.logging_middleware import LoggingMiddleware
from app.modules.catalog.presentation.router import router as catalog_router
from app.modules.inventory.presentation.router import router as inventory_router
from app.modules.transfers.presentation.router import router as transfers_router
from app.modules.purchasing.presentation.router import router as purchasing_router

configure_logging(json_logs=settings.log_json, log_level=settings.log_level)

app = FastAPI(
    version="0.1.0",
    title="Restaurant ERP Template",
)

app.add_middleware(LoggingMiddleware)
register_exception_handlers(app)

app.include_router(catalog_router, prefix="/api/v1/catalog")
app.include_router(inventory_router, prefix="/api/v1/inventory")
app.include_router(transfers_router, prefix="/api/v1/transfers")
app.include_router(purchasing_router, prefix="/api/v1/purchasing")


@app.get("/api/v1/health")
async def health() -> dict:
    return {"data": {"status": "ok"}}
