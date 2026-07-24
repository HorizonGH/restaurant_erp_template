from fastapi import FastAPI

from app.core.logging import configure_logging
from app.core.settings import settings
from app.core.shared.presentation.exception_handlers import register_exception_handlers
from app.middlewares.logging_middleware import LoggingMiddleware

configure_logging(json_logs=settings.log_json, log_level=settings.log_level)

app = FastAPI(
    version="0.1.0",
    title="Restaurant ERP Template",
)

app.add_middleware(LoggingMiddleware)
register_exception_handlers(app)


@app.get("/")
async def health():
    return {"detail": "ok"}
