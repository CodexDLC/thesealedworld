from fastapi import FastAPI

from src.backend.chat.api.router import router as chat_rest_router
from src.backend.chat.api.ws import router as chat_ws_router
from src.backend.chat.core.lifespan import lifespan
from src.backend.config.settings import settings
from src.shared.log_middleware import LogContextMiddleware
from src.shared.logging_config import setup_logging
from src.shared.metrics_endpoint import metrics_router
from src.shared.metrics_middleware import PrometheusMiddleware

setup_logging(
    settings=settings,
    service_name="chat",
    intercept_loggers=["uvicorn", "fastapi"],
    log_levels={"httpx": 30},
)

app = FastAPI(title="TurnBasedMMORPG Chat Service", lifespan=lifespan)

app.add_middleware(PrometheusMiddleware, service_name="chat")
app.add_middleware(LogContextMiddleware)
app.include_router(chat_ws_router)
app.include_router(chat_rest_router)
app.include_router(metrics_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
