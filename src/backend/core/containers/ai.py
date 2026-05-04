import logging

from fastapi import FastAPI

from src.backend.core.ai import AIService

log = logging.getLogger(__name__)


class AIContainer:
    """Manages AI Services and Prompt Routers."""

    async def bootstrap(self, app: FastAPI) -> None:
        log.info("Bootstrapping AI Services...")
        app.state.ai = AIService()
        log.info("AI bootstrap finished")
