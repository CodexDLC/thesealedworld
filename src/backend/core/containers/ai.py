from fastapi import FastAPI
from loguru import logger as log

from src.backend.core.ai import AIService


class AIContainer:
    """Manages AI Services and Prompt Routers."""

    async def bootstrap(self, app: FastAPI) -> None:
        log.info("AiServicesBootstrapStarted")
        app.state.ai = AIService()
        log.info("AiServicesBootstrapFinished")
