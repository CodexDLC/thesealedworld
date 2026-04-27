# backend/main.py
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from src.backend.core.config import settings
from src.backend.core.database import async_engine, get_session_context, run_alembic_migrations
from src.backend.core.exceptions import BaseAPIException, api_exception_handler
from src.backend.domains.user_features.scenario.resources.loaders.scenario_loader import ScenarioLoader
from src.backend.router import api_router, tags_metadata
from src.shared.core.logger import setup_logging
from src.shared.schemas.errors import ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Настройка логгера с меткой "backend"
    setup_logging(settings, service_name="backend")
    logger.info("🚀 Server starting... Project: {name}", name=settings.project_name)

    if settings.debug:
        logger.debug("🐛 Debug mode is ENABLED")
    else:
        logger.info("🔒 Production mode: Swagger UI is DISABLED")

    if settings.auto_migrate:
        logger.info("Running database migrations (AUTO_MIGRATE=True)...")
        # Пока закомментировано внутри функции, но вызов оставляем
        await run_alembic_migrations()
    else:
        logger.warning("⚠️ AUTO_MIGRATE=False: Skipping migrations. Run 'alembic upgrade head' manually.")

    # --- SCENARIO LOADER ---
    logger.info("Loading scenarios...")
    try:
        async with get_session_context() as session:
            loader = ScenarioLoader(session)
            await loader.load_all_scenarios()
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to load scenarios on startup: {e}")

    yield

    logger.info("🛑 Server shutting down... Closing DB connections...")
    await async_engine.dispose()
    logger.info("👋 Bye!")


# --- DOCS CONFIGURATION ---
docs_url = "/docs" if settings.debug else None
redoc_url = "/redoc" if settings.debug else None
openapi_url = f"{settings.api_v1_str}/openapi.json" if settings.debug else None

# --- GLOBAL ERROR RESPONSES ---
responses: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Bad Request"},
    401: {"model": ErrorResponse, "description": "Unauthorized"},
    403: {"model": ErrorResponse, "description": "Forbidden"},
    404: {"model": ErrorResponse, "description": "Not Found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
    422: {"model": ErrorResponse, "description": "Validation Error"},
    500: {"model": ErrorResponse, "description": "Internal Server Error"},
}

app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    responses=responses,
)

# --- CORS SETUP ---
if settings.debug:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
elif settings.allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# --- EXCEPTION HANDLERS ---

# 1. Наши кастомные ошибки (бизнес-логика)
app.add_exception_handler(BaseAPIException, api_exception_handler)  # type: ignore


# 2. Глобальный перехватчик всех остальных ошибок (Last Resort)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Если DEBUG=True, позволяем FastAPI показать стандартную страницу с трейсбеком
    if settings.debug:
        raise exc

    # В проде логируем ошибку и отдаем нейтральный JSON
    logger.exception(f"🔥 Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "An unexpected error occurred. Please try again later.",
            }
        },
    )


app.include_router(api_router, prefix=settings.api_v1_str)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.project_name}


@app.get("/", tags=["System"])
async def root() -> dict[str, str]:
    if settings.debug:
        return {"message": f"Welcome to {settings.project_name} API. Go to /docs for Swagger."}
    return {"message": f"Welcome to {settings.project_name} API."}


if __name__ == "__main__":
    import uvicorn

    # Запуск сервера при прямом исполнении файла
    # reload=settings.debug позволяет авто-перезагрузку при изменении кода (если debug=True)
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
