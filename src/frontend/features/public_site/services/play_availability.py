from __future__ import annotations

from urllib.parse import urljoin

import httpx
from loguru import logger

from src.frontend.config.settings import settings


def build_play_url(path: str = "/game-lobby") -> str:
    base = settings.play_public_base_url.rstrip("/")
    if not base:
        base = "/game-lobby"
    if base.startswith("/"):
        return base if path == "/game-lobby" else path
    return urljoin(f"{base}/", path.lstrip("/"))


class PlayAvailabilityService:
    async def is_available(self) -> bool:
        base = settings.play_internal_base_url.strip().rstrip("/")
        if not base:
            return True

        health_url = f"{base}/health"
        try:
            async with httpx.AsyncClient(timeout=settings.play_health_timeout_seconds) as client:
                response = await client.get(health_url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.bind(health_url=health_url, error=str(exc)).warning("FrontendPlayHealthUnavailable")
            return False
        return True
